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
