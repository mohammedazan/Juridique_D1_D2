#!/usr/bin/env python3
"""
D1 analysis layer (refine/extend only).

This script reads existing outputs without rebuilding the dataset and generates:
  - processed/analysis.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List

csv.field_size_limit(10**9)


def fold_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def word_count(text: str) -> int:
    return len((text or "").split())


def percentage(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((count / total) * 100.0, 2)


def classify_question(question: str) -> str:
    q = fold_text(question)

    definition_kw = [
        "qu'est-ce que",
        "qu est-ce que",
        "definition",
        "definit",
        "que signifie",
        "que veut dire",
        "qu'appelle-t-on",
        "qu appelle-t-on",
    ]
    condition_kw = [
        "condition",
        "conditions",
        "dans quel cas",
        "dans quels cas",
        "a quelle condition",
        "sous quelle condition",
        "circonstances",
        "lorsque",
        "quand",
        "si ",
    ]
    procedure_kw = [
        "comment",
        "procedure",
        "etapes",
        "demarche",
        "formalites",
        "modalites",
        "transmis",
        "transmettre",
        "traites",
        "traiter",
    ]
    obligation_kw = [
        "doit",
        "doivent",
        "obligation",
        "obligations",
        "obligatoire",
        "tenu de",
        "est tenu",
        "il faut",
    ]

    # Fixed precedence:
    # definition -> condition -> procedure -> obligation -> other
    if any(k in q for k in definition_kw):
        return "definition"
    if any(k in q for k in condition_kw):
        return "condition"
    if any(k in q for k in procedure_kw):
        return "procedure"
    if any(k in q for k in obligation_kw):
        return "obligation"
    return "other"


def compute_question_types(samples: List[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    total = len(samples)
    counts = Counter(classify_question(s["question"]) for s in samples)
    labels = ["definition", "condition", "procedure", "obligation", "other"]
    return {
        label: {"count": counts.get(label, 0), "percent": percentage(counts.get(label, 0), total)}
        for label in labels
    }


def compute_length_analysis(samples: List[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    q_len = [word_count(s["question"]) for s in samples]
    a_len = [word_count(s["answer"]) for s in samples]
    c_len = [word_count(s["context"]) for s in samples]

    def stats(values: List[int]) -> Dict[str, float]:
        if not values:
            return {"avg": 0.0, "min": 0, "max": 0}
        return {
            "avg": round(sum(values) / len(values), 2),
            "min": min(values),
            "max": max(values),
        }

    return {
        "question_length_words": stats(q_len),
        "answer_length_words": stats(a_len),
        "context_length_words": stats(c_len),
    }


def compute_answer_type_distribution(samples: List[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    counts = Counter()
    for s in samples:
        n = word_count(s["answer"])
        if n <= 5:
            counts["short"] += 1
        elif n <= 15:
            counts["medium"] += 1
        else:
            counts["long"] += 1

    total = len(samples)
    return {
        "short": {"count": counts.get("short", 0), "percent": percentage(counts.get("short", 0), total)},
        "medium": {
            "count": counts.get("medium", 0),
            "percent": percentage(counts.get("medium", 0), total),
        },
        "long": {"count": counts.get("long", 0), "percent": percentage(counts.get("long", 0), total)},
    }


def compute_filtering_impact(
    qa_csv_path: Path,
    final_dataset_size: int,
    window_chars: int,
) -> Dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Reuse the same filtering/extractive logic from core pipeline in read-only mode.
    from scripts.build_legal_qa_dataset import (  # pylint: disable=import-error
        build_local_context,
        contains_arabic,
        extract_extractive_answer,
        french_score,
        is_latin_dominant,
        normalize_text,
    )

    counts = {
        "initial_size": 0,
        "after_language_filter": 0,
        "after_extractive_filter": 0,
        "final_size": final_dataset_size,
    }

    with qa_csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            counts["initial_size"] += 1

            question = normalize_text(row.get("Question", ""))
            answer = normalize_text(row.get("Answer", ""))
            context = normalize_text(row.get("Context", ""))

            if not question or not answer or not context:
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
                continue
            counts["after_language_filter"] += 1

            extracted_answer, _ = extract_extractive_answer(answer, context)
            if not extracted_answer:
                continue

            local_context = build_local_context(context, extracted_answer, window_chars)
            if not local_context or extracted_answer not in local_context:
                continue

            counts["after_extractive_filter"] += 1

    counts["monotonic_non_increasing"] = (
        counts["initial_size"] >= counts["after_language_filter"] >= counts["after_extractive_filter"]
        >= counts["final_size"]
    )
    counts["method_note"] = (
        "Counts were recomputed in read-only mode from DATASET/qa.csv using the same "
        "language and extractive rules as the existing pipeline."
    )
    return counts


def pick_examples(samples: List[Dict[str, str]], seed: int, n: int = 5) -> List[Dict[str, str]]:
    if not samples:
        return []
    if len(samples) <= n:
        selected = list(samples)
    else:
        selected = random.Random(seed).sample(samples, n)

    return [
        {
            "id": s["id"],
            "question": s["question"],
            "context": s["context"],
            "answer": s["answer"],
        }
        for s in selected
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate D1 analysis from existing dataset outputs")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("processed/legal_qa_dataset.json"),
        help="Path to existing processed dataset",
    )
    parser.add_argument(
        "--qa-csv",
        type=Path,
        default=Path("DATASET/qa.csv"),
        help="Path to source qa.csv (read-only for impact counters)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("processed/analysis.json"),
        help="Path to analysis output json",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed for deterministic example sampling")
    parser.add_argument(
        "--window-chars",
        type=int,
        default=600,
        help="Window chars used by current pipeline (for filtering impact consistency)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    samples = json.loads(args.dataset.read_text(encoding="utf-8"))
    final_size = len(samples)

    analysis = {
        "question_types": compute_question_types(samples),
        "length_analysis": compute_length_analysis(samples),
        "answer_type_distribution": compute_answer_type_distribution(samples),
        "filtering_impact": compute_filtering_impact(
            qa_csv_path=args.qa_csv,
            final_dataset_size=final_size,
            window_chars=args.window_chars,
        ),
        "sample_examples": pick_examples(samples, seed=args.seed, n=5),
        "metadata": {
            "seed": args.seed,
            "dataset_path": str(args.dataset),
            "qa_csv_path": str(args.qa_csv),
            "classification_precedence": [
                "definition",
                "condition",
                "procedure",
                "obligation",
                "other",
            ],
            "answer_length_bins_words": {"short": "<=5", "medium": "6-15", "long": ">15"},
            "method": "rule_based_read_only_analysis",
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "final_size": final_size}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
