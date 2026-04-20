# REPORT — Pipeline Dataset QA Juridique (D1 + D2)

## 1. Decisions Taken
- Schéma retenu: `id`, `context`, `question`, `answer`, `language`, `difficulty`, `split`.
- Source unique utilisée: `DATASET/qa.csv`.
- Filtrage linguistique: suppression des entrées non FR via rejet du script arabe dans `Question/Answer`, dominance latine, et score minimal de stopwords FR dans la question.
- Contrainte extractive: reconstruction d'un span de réponse présent dans le contexte.
- Difficulté: règle par tertiles de longueur (`context_words` + `answer_words`) puis projection en `easy/medium/hard`.
- Sélection finale: stratifiée par difficulté, taille cible 100 si disponible.

## 2. Data Source Used
- Fichier: `DATASET/qa.csv`.
- Colonnes exploitées: `Question`, `Answer`, `Context`.
- Colonne ignorée pour la sortie: `file_name` (utilisée uniquement en source).

## 3. Transformations Applied
- Normalisation Unicode NFKC et normalisation des espaces.
- Suppression des lignes vides.
- Filtrage FR (heuristiques simples, sans NLP avancé).
- Nettoyage des préambules de réponse (ex: "Absolument", "D'après", etc.).
- Génération d'une réponse extractive via matching déterministe sur texte normalisé.
- Réduction du contexte à une fenêtre locale de ±600 caractères autour de la réponse.
- Déduplication sur `(question, answer, context)` normalisés.
- Attribution de difficulté, échantillonnage stratifié, split 70/15/15, génération des statistiques.

## 4. Problems Encountered
- Forte proportion de réponses non extractives en l'état brut.
- Présence de contenu multilingue (arabe + français) dans le fichier source.
- Contextes parfois très longs, impactant la lisibilité des exemples.

## 5. Fixes Applied
- Reconstruction extractive de la réponse à partir de segments présents dans le contexte.
- Filtrage linguistique strict pour ne conserver que des exemples FR.
- Fenêtrage local du contexte pour réduire la taille sans perdre la contrainte extractive.

## 6. Statistics Summary
- Total samples: 100
- Avg context length (words): 196.06
- Avg answer length (words): 11.15
- Difficulty distribution: {"easy": 34, "medium": 33, "hard": 33}
- Split distribution: {"train": 70, "val": 15, "test": 15}

## 7. Final Dataset Description
- Dossier de sortie: `processed`
- Taille cible demandée: 100
- Format final: JSON list d'échantillons QA extractifs en français.
- Chaque entrée contient un identifiant déterministe, une question, un contexte local, une réponse extractive, une difficulté et un split.

## Annexe — Compteurs Pipeline
- Lignes lues: 24973
- Lignes supprimées (vides): 11
- Lignes supprimées (filtre langue): 12085
- Lignes supprimées (pas de span extractif): 7342
- Lignes supprimées (contexte local invalide): 0
- Doublons supprimés: 9
- Candidats avant échantillonnage: 5526
- Match mode full: 70
- Match mode segment: 5456

## Paramètres d'exécution
- seed: 42
- window_chars: 600

## DATA ANALYSIS

### A. Question Types Analysis (Rule-Based)

Classification precedence (deterministic): `definition` -> `condition` -> `procedure` -> `obligation` -> `other`.

| Type | Count | Percent |
|---|---:|---:|
| definition | 4 | 4.00% |
| condition | 12 | 12.00% |
| procedure | 31 | 31.00% |
| obligation | 9 | 9.00% |
| other | 44 | 44.00% |

Interpretation: the dataset is dominated by procedural and general legal questions (`procedure + other = 75%`), with fewer explicit definition/obligation forms.

### B. Length Analysis (Words)

| Field | Average | Min | Max |
|---|---:|---:|---:|
| question | 22.81 | 10 | 41 |
| answer | 11.15 | 2 | 41 |
| context | 196.06 | 87 | 241 |

Interpretation: contexts are much longer than answers, which is consistent with extractive QA and local context windowing.

### C. Answer Type Analysis

Bins: `short <= 5`, `medium 6-15`, `long > 15`.

| Answer Type | Count | Percent |
|---|---:|---:|
| short | 25 | 25.00% |
| medium | 54 | 54.00% |
| long | 21 | 21.00% |

Interpretation: medium-length answers are the majority, indicating concise but non-trivial extractive spans.

### D. Dataset Filtering Impact

| Stage | Size |
|---|---:|
| initial_size | 24973 |
| after_language_filter | 12877 |
| after_extractive_filter | 5535 |
| final_size | 100 |

Method note: counts were recomputed in read-only mode from `DATASET/qa.csv` using the same language and extractive rules as the existing pipeline.

### E. Sample Examples (5 Real Samples, seed=42)

1. `id: legal_qa_000082`
question: Quelles sont les obligations des employeurs concernant les permissions d'absence pour les salaries elus au conseil de la region, et comment le temps passe en session est-il gere ?
context (excerpt): ... Les employeurs sont tenus d'accorder aux salaries de leurs entreprises elus en tant que membres du conseil de la region ... La permission d'absence est accordee a plein traitement ...
answer: aux reunions des commissions dont ils sont membres

2. `id: legal_qa_000015`
question: Dans quelles circonstances les frais d'accouchement sont-ils inclus dans le remboursement partiel des depenses de sante ?
context (excerpt): ... Les frais d'accouchement ne sont pas exclus du remboursement partiel ... honoraires du medecin specialiste appeles dans les cas d'accouchements difficiles ...
answer: ou les honoraires du medecin specialiste appele par le medecin ordinaire, dans les cas d'accouchements difficiles

3. `id: legal_qa_000004`
question: Decrivez les trois niveaux du systeme de detection requis pour les depots, armoires et fabriques, en precisant les technologies possibles pour chaque niveau.
context (excerpt): ... Niveau de detection 2 ... detection perimetrique ... detection a la deterioration sous l'effet de chocs ... Niveau de detection 3 ... detection interieure ...
answer: detection a la deterioration, sous l'effet par exemple de chocs ou de phenomenes sismiques, des issues, des ouvrants, des parois ou des parties de parois de faible resistance mecanique

4. `id: legal_qa_000095`
question: Quelles sont les conditions pour etre candidat au Prix Mohammed VI de l'art de la calligraphie ?
context (excerpt): ... Le candidat a l'obtention du prix Mohammed VI de l'art de la calligraphie ... doit etre une personne physique, de nationalite marocaine ...
answer: etre une personne physique

5. `id: legal_qa_000036`
question: Quelles sont les limites d'endettement d'un OPCI, tant pour les emprunts lies aux actifs immobiliers que pour les emprunts de tresorerie, et comment ces emprunts doivent-ils etre utilises ?
context (excerpt): ... il est tenu compte de l'ensemble des emprunts et dettes souscrits directement par l'OPCI ... conformement au reglement de gestion ...
answer: il est tenu compte de l'ensemble des emprunts et dettes souscrits directement par l'OPCI
