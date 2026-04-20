#!/usr/bin/env python3
"""
Pipeline D1 + D2 pour construire un dataset QA juridique FR à partir de DATASET/qa.csv.

Sorties:
  - processed/legal_qa_dataset.json
  - processed/train.json
  - processed/val.json
  - processed/test.json
  - processed/stats.json
  - REPORT.md
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

csv.field_size_limit(10**9)

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\!\?\;\:])\s+|\n+")
CLAUSE_SPLIT_RE = re.compile(r"[,؛،]+")
WS_RE = re.compile(r"\s+")

FRENCH_STOPWORDS = {
    "le",
    "la",
    "les",
    "de",
    "des",
    "du",
    "un",
    "une",
    "et",
    "ou",
    "dans",
    "pour",
    "sur",
    "avec",
    "par",
    "aux",
    "au",
    "en",
    "que",
    "qui",
    "est",
    "sont",
    "ce",
    "cette",
    "ces",
    "droit",
    "loi",
    "article",
    "ministre",
    "maroc",
}

ANSWER_PREFIXES = (
    "absolument",
    "bien sûr",
    "voici",
    "d'après",
    "selon",
    "en se basant",
    "en se référant",
    "au regard",
    "en vertu",
)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\ufeff", " ")
    return WS_RE.sub(" ", text).strip()


def normalize_for_match(text: str, keep_map: bool = False):
    out_chars: List[str] = []
    idx_map: List[int] = []
    prev_space = False
    source = text or ""

    for i, ch in enumerate(source):
        cl = ch.lower()
        cat = unicodedata.category(cl)
        if cat.startswith("L") or cat.startswith("N"):
            out_chars.append(cl)
            if keep_map:
                idx_map.append(i)
            prev_space = False
        elif cl.isspace() or cat.startswith("P") or cat.startswith("S"):
            if out_chars and not prev_space:
                out_chars.append(" ")
                if keep_map:
                    idx_map.append(i)
                prev_space = True
        else:
            continue

    if out_chars and out_chars[-1] == " ":
        out_chars.pop()
        if keep_map:
            idx_map.pop()

    normalized = "".join(out_chars)
    if keep_map:
        return normalized, idx_map
    return normalized


def contains_arabic(text: str) -> bool:
    return bool(ARABIC_RE.search(text or ""))


def is_latin_dominant(text: str) -> bool:
    if not text:
        return False
    a = len(ARABIC_RE.findall(text))
    l = len(LATIN_RE.findall(text))
    return l > a and l > 0


def french_score(text: str) -> int:
    tokens = [t.lower() for t in WORD_RE.findall(text or "")]
    if not tokens:
        return 0
    return sum(1 for t in tokens if t in FRENCH_STOPWORDS)


def strip_answer_preface(answer: str) -> str:
    answer = normalize_text(answer)
    low = answer.lower()
    if any(low.startswith(prefix) for prefix in ANSWER_PREFIXES):
        if ":" in answer[:300]:
            answer = answer.split(":", 1)[1].strip()

    answer = re.sub(r"^[-*#\s]+", "", answer)
    answer = re.sub(r"^\d+\.\s*", "", answer)
    return normalize_text(answer)


def locate_span_in_context(
    candidate: str, context: str, normalized_context: str, context_index_map: Sequence[int]
) -> Optional[str]:
    normalized_candidate = normalize_for_match(candidate, keep_map=False)
    if len(normalized_candidate) < 20:
        return None

    pos = normalized_context.find(normalized_candidate)
    if pos == -1:
        return None

    start = context_index_map[pos]
    end = context_index_map[pos + len(normalized_candidate) - 1] + 1
    span = normalize_text(context[start:end])
    if not span:
        return None
    if span not in context:
        return None
    return span


def build_answer_candidates(answer: str) -> List[str]:
    base = strip_answer_preface(answer)
    if not base:
        return []

    candidates = [base]
    candidates.extend(seg.strip(" -\t") for seg in SENTENCE_SPLIT_RE.split(base))
    candidates.extend(seg.strip(" -\t") for seg in CLAUSE_SPLIT_RE.split(base))

    cleaned = []
    seen = set()
    for c in candidates:
        c = normalize_text(c)
        if not c:
            continue
        key = c.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(c)

    cleaned.sort(key=len, reverse=True)
    return cleaned


def extract_extractive_answer(answer: str, context: str) -> Tuple[Optional[str], Optional[str]]:
    normalized_context, context_index_map = normalize_for_match(context, keep_map=True)
    if not normalized_context:
        return None, None

    candidates = build_answer_candidates(answer)
    if not candidates:
        return None, None

    for idx, candidate in enumerate(candidates):
        span = locate_span_in_context(candidate, context, normalized_context, context_index_map)
        if span:
            mode = "full" if idx == 0 else "segment"
            return span, mode

    return None, None


def build_local_context(context: str, answer: str, window_chars: int) -> Optional[str]:
    pos = context.find(answer)
    if pos == -1:
        return None

    start = max(0, pos - window_chars)
    end = min(len(context), pos + len(answer) + window_chars)
    local_context = normalize_text(context[start:end])

    if answer in local_context:
        return local_context

    full_context = normalize_text(context)
    if answer in full_context:
        return full_context

    return None


def dedup_key(question: str, answer: str, context: str) -> Tuple[str, str, str]:
    return (
        normalize_for_match(question, keep_map=False),
        normalize_for_match(answer, keep_map=False),
        normalize_for_match(context, keep_map=False),
    )


def percentile(values: Sequence[int], p: float) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    idx = round((p / 100.0) * (len(sorted_values) - 1))
    return sorted_values[idx]


def assign_difficulty(samples: List[Dict[str, str]]) -> None:
    context_words = [len(s["context"].split()) for s in samples]
    answer_words = [len(s["answer"].split()) for s in samples]

    c_q1 = percentile(context_words, 33.33)
    c_q2 = percentile(context_words, 66.66)
    a_q1 = percentile(answer_words, 33.33)
    a_q2 = percentile(answer_words, 66.66)

    def bucket(value: int, q1: int, q2: int) -> int:
        if value <= q1:
            return 0
        if value <= q2:
            return 1
        return 2

    for sample in samples:
        c_bucket = bucket(len(sample["context"].split()), c_q1, c_q2)
        a_bucket = bucket(len(sample["answer"].split()), a_q1, a_q2)
        score = c_bucket + a_bucket
        if score <= 1:
            sample["difficulty"] = "easy"
        elif score == 2:
            sample["difficulty"] = "medium"
        else:
            sample["difficulty"] = "hard"


def stratified_sample(
    samples: List[Dict[str, str]], target_size: int, seed: int
) -> List[Dict[str, str]]:
    if len(samples) <= target_size:
        return list(samples)

    rng = random.Random(seed)
    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for sample in samples:
        groups[sample["difficulty"]].append(sample)

    labels = ["easy", "medium", "hard"]
    for label in labels:
        rng.shuffle(groups[label])

    base = target_size // 3
    rem = target_size % 3
    desired = {label: base for label in labels}
    for i in range(rem):
        desired[labels[i]] += 1

    selected: List[Dict[str, str]] = []
    leftovers: List[Dict[str, str]] = []
    for label in labels:
        take = min(desired[label], len(groups[label]))
        selected.extend(groups[label][:take])
        leftovers.extend(groups[label][take:])

    if len(selected) < target_size:
        rng.shuffle(leftovers)
        selected.extend(leftovers[: target_size - len(selected)])

    rng.shuffle(selected)
    return selected[:target_size]


def split_sizes(total: int) -> Tuple[int, int, int]:
    train = int(total * 0.70)
    val = int(total * 0.15)
    test = total - train - val
    return train, val, test


def split_dataset(
    samples: List[Dict[str, str]], seed: int
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    shuffled = list(samples)
    random.Random(seed).shuffle(shuffled)
    n_train, n_val, _ = split_sizes(len(shuffled))
    train = shuffled[:n_train]
    val = shuffled[n_train : n_train + n_val]
    test = shuffled[n_train + n_val :]
    return train, val, test


def compute_stats(samples: Sequence[Dict[str, str]]) -> Dict[str, object]:
    total = len(samples)
    context_lengths = [len(s["context"].split()) for s in samples]
    answer_lengths = [len(s["answer"].split()) for s in samples]
    difficulty_dist = Counter(s["difficulty"] for s in samples)
    split_dist = Counter(s["split"] for s in samples)

    avg_context = round(sum(context_lengths) / total, 2) if total else 0.0
    avg_answer = round(sum(answer_lengths) / total, 2) if total else 0.0

    return {
        "total_samples": total,
        "avg_context_length": avg_context,
        "avg_answer_length": avg_answer,
        "length_unit": "words",
        "difficulty_distribution": {
            "easy": difficulty_dist.get("easy", 0),
            "medium": difficulty_dist.get("medium", 0),
            "hard": difficulty_dist.get("hard", 0),
        },
        "split_distribution": {
            "train": split_dist.get("train", 0),
            "val": split_dist.get("val", 0),
            "test": split_dist.get("test", 0),
        },
    }


def validate_samples(samples: Sequence[Dict[str, str]]) -> None:
    required = {"id", "context", "question", "answer", "language", "difficulty", "split"}
    seen_ids = set()
    seen_keys = set()
    valid_splits = {"train", "val", "test"}
    valid_difficulties = {"easy", "medium", "hard"}

    for sample in samples:
        if set(sample.keys()) != required:
            raise ValueError(f"Schéma invalide pour l'échantillon: {sample.keys()}")

        for key in required:
            if not isinstance(sample[key], str):
                raise ValueError(f"Type invalide pour {key}: {type(sample[key])}")
            if key in {"context", "question", "answer", "id"} and not sample[key].strip():
                raise ValueError(f"Champ vide détecté: {key}")

        if sample["language"] != "fr":
            raise ValueError("Champ language invalide (attendu: fr)")

        if sample["split"] not in valid_splits:
            raise ValueError(f"Split invalide: {sample['split']}")

        if sample["difficulty"] not in valid_difficulties:
            raise ValueError(f"Difficulté invalide: {sample['difficulty']}")

        if sample["answer"] not in sample["context"]:
            raise ValueError("Contrainte extractive violée: answer non contenu dans context")

        if sample["id"] in seen_ids:
            raise ValueError(f"ID dupliqué: {sample['id']}")
        seen_ids.add(sample["id"])

        key = dedup_key(sample["question"], sample["answer"], sample["context"])
        if key in seen_keys:
            raise ValueError("Doublon détecté après normalisation")
        seen_keys.add(key)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def make_report(
    report_path: Path,
    input_path: Path,
    output_dir: Path,
    target_size: int,
    seed: int,
    window_chars: int,
    process_counts: Counter,
    stats: Dict[str, object],
) -> None:
    lines = [
        "# REPORT — Pipeline Dataset QA Juridique (D1 + D2)",
        "",
        "## 1. Decisions Taken",
        "- Schéma retenu: `id`, `context`, `question`, `answer`, `language`, `difficulty`, `split`.",
        "- Source unique utilisée: `DATASET/qa.csv`.",
        "- Filtrage linguistique: suppression des entrées non FR via rejet du script arabe dans `Question/Answer`, dominance latine, et score minimal de stopwords FR dans la question.",
        "- Contrainte extractive: reconstruction d'un span de réponse présent dans le contexte.",
        "- Difficulté: règle par tertiles de longueur (`context_words` + `answer_words`) puis projection en `easy/medium/hard`.",
        "- Sélection finale: stratifiée par difficulté, taille cible 100 si disponible.",
        "",
        "## 2. Data Source Used",
        f"- Fichier: `{input_path.as_posix()}`.",
        "- Colonnes exploitées: `Question`, `Answer`, `Context`.",
        "- Colonne ignorée pour la sortie: `file_name` (utilisée uniquement en source).",
        "",
        "## 3. Transformations Applied",
        "- Normalisation Unicode NFKC et normalisation des espaces.",
        "- Suppression des lignes vides.",
        "- Filtrage FR (heuristiques simples, sans NLP avancé).",
        "- Nettoyage des préambules de réponse (ex: \"Absolument\", \"D'après\", etc.).",
        "- Génération d'une réponse extractive via matching déterministe sur texte normalisé.",
        f"- Réduction du contexte à une fenêtre locale de ±{window_chars} caractères autour de la réponse.",
        "- Déduplication sur `(question, answer, context)` normalisés.",
        "- Attribution de difficulté, échantillonnage stratifié, split 70/15/15, génération des statistiques.",
        "",
        "## 4. Problems Encountered",
        "- Forte proportion de réponses non extractives en l'état brut.",
        "- Présence de contenu multilingue (arabe + français) dans le fichier source.",
        "- Contextes parfois très longs, impactant la lisibilité des exemples.",
        "",
        "## 5. Fixes Applied",
        "- Reconstruction extractive de la réponse à partir de segments présents dans le contexte.",
        "- Filtrage linguistique strict pour ne conserver que des exemples FR.",
        "- Fenêtrage local du contexte pour réduire la taille sans perdre la contrainte extractive.",
        "",
        "## 6. Statistics Summary",
        f"- Total samples: {stats['total_samples']}",
        f"- Avg context length (words): {stats['avg_context_length']}",
        f"- Avg answer length (words): {stats['avg_answer_length']}",
        f"- Difficulty distribution: {json.dumps(stats['difficulty_distribution'], ensure_ascii=False)}",
        f"- Split distribution: {json.dumps(stats['split_distribution'], ensure_ascii=False)}",
        "",
        "## 7. Final Dataset Description",
        f"- Dossier de sortie: `{output_dir.as_posix()}`",
        f"- Taille cible demandée: {target_size}",
        "- Format final: JSON list d'échantillons QA extractifs en français.",
        "- Chaque entrée contient un identifiant déterministe, une question, un contexte local, une réponse extractive, une difficulté et un split.",
        "",
        "## Annexe — Compteurs Pipeline",
        f"- Lignes lues: {process_counts['rows_total']}",
        f"- Lignes supprimées (vides): {process_counts['drop_empty']}",
        f"- Lignes supprimées (filtre langue): {process_counts['drop_language']}",
        f"- Lignes supprimées (pas de span extractif): {process_counts['drop_no_extractive_span']}",
        f"- Lignes supprimées (contexte local invalide): {process_counts['drop_bad_local_context']}",
        f"- Doublons supprimés: {process_counts['drop_duplicate']}",
        f"- Candidats avant échantillonnage: {process_counts['kept_candidates']}",
        f"- Match mode full: {process_counts['match_mode_full']}",
        f"- Match mode segment: {process_counts['match_mode_segment']}",
        "",
        "## Paramètres d'exécution",
        f"- seed: {seed}",
        f"- window_chars: {window_chars}",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(
    input_path: Path, output_dir: Path, target_size: int, seed: int, window_chars: int
) -> Dict[str, object]:
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {input_path}")

    process_counts: Counter = Counter()
    candidates: List[Dict[str, str]] = []
    seen = set()

    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required_cols = {"Question", "Answer", "Context", "file_name"}
        if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"Colonnes manquantes. Attendu au moins {sorted(required_cols)}, "
                f"reçu: {reader.fieldnames}"
            )

        for row in reader:
            process_counts["rows_total"] += 1

            question = normalize_text(row.get("Question", ""))
            answer = normalize_text(row.get("Answer", ""))
            context = normalize_text(row.get("Context", ""))

            if not question or not answer or not context:
                process_counts["drop_empty"] += 1
                continue

            if (
                contains_arabic(question)
                or contains_arabic(answer)
                or not is_latin_dominant(question)
                or not is_latin_dominant(answer)
                or not is_latin_dominant(context)
                or french_score(question) < 2
                or french_score(context[:2000]) < 10
            ):
                process_counts["drop_language"] += 1
                continue

            extracted_answer, mode = extract_extractive_answer(answer, context)
            if not extracted_answer:
                process_counts["drop_no_extractive_span"] += 1
                continue

            local_context = build_local_context(context, extracted_answer, window_chars)
            if not local_context or extracted_answer not in local_context:
                process_counts["drop_bad_local_context"] += 1
                continue

            key = dedup_key(question, extracted_answer, local_context)
            if key in seen:
                process_counts["drop_duplicate"] += 1
                continue
            seen.add(key)

            process_counts["kept_candidates"] += 1
            if mode == "full":
                process_counts["match_mode_full"] += 1
            else:
                process_counts["match_mode_segment"] += 1

            candidates.append(
                {
                    "question": question,
                    "answer": extracted_answer,
                    "context": local_context,
                    "language": "fr",
                }
            )

    if not candidates:
        raise RuntimeError("Aucun candidat valide après nettoyage/filtrage.")

    assign_difficulty(candidates)
    selected = stratified_sample(candidates, target_size=target_size, seed=seed)
    train, val, test = split_dataset(selected, seed=seed)

    output_samples: List[Dict[str, str]] = []
    next_id = 1
    for split_name, split_set in (("train", train), ("val", val), ("test", test)):
        for sample in split_set:
            output_samples.append(
                {
                    "id": f"legal_qa_{next_id:06d}",
                    "context": sample["context"],
                    "question": sample["question"],
                    "answer": sample["answer"],
                    "language": "fr",
                    "difficulty": sample["difficulty"],
                    "split": split_name,
                }
            )
            next_id += 1

    validate_samples(output_samples)
    stats = compute_stats(output_samples)

    train_samples = [s for s in output_samples if s["split"] == "train"]
    val_samples = [s for s in output_samples if s["split"] == "val"]
    test_samples = [s for s in output_samples if s["split"] == "test"]

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "legal_qa_dataset.json", output_samples)
    write_json(output_dir / "train.json", train_samples)
    write_json(output_dir / "val.json", val_samples)
    write_json(output_dir / "test.json", test_samples)
    write_json(output_dir / "stats.json", stats)

    return {
        "stats": stats,
        "process_counts": process_counts,
        "num_candidates": len(candidates),
        "num_selected": len(output_samples),
        "files": {
            "dataset": str(output_dir / "legal_qa_dataset.json"),
            "train": str(output_dir / "train.json"),
            "val": str(output_dir / "val.json"),
            "test": str(output_dir / "test.json"),
            "stats": str(output_dir / "stats.json"),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FR legal QA dataset from qa.csv")
    parser.add_argument("--input", type=Path, required=True, help="Path to qa.csv")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--target-size", type=int, default=100, help="Final target size")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--window-chars",
        type=int,
        default=600,
        help="Number of chars before and after answer in local context",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        input_path=args.input,
        output_dir=args.output,
        target_size=args.target_size,
        seed=args.seed,
        window_chars=args.window_chars,
    )

    report_path = Path("REPORT.md")
    make_report(
        report_path=report_path,
        input_path=args.input,
        output_dir=args.output,
        target_size=args.target_size,
        seed=args.seed,
        window_chars=args.window_chars,
        process_counts=result["process_counts"],
        stats=result["stats"],
    )

    summary = {
        "selected_samples": result["num_selected"],
        "candidates_before_sampling": result["num_candidates"],
        "stats": result["stats"],
        "files": result["files"],
        "report": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
