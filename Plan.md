# 📘 PLAN.MD — Legal Data Pipeline (D1 + D2 Adaptation)

## 🎯 Objective

Build a **clean, unified legal dataset pipeline** based on the original project structure (D1, D2), while adapting it from medical datasets to a **Juridique (legal) context**.

Final goal:

* Structured Legal QA dataset
* Unified format (JSON)
* Clean preprocessing pipeline
* Train / Validation / Test splits
* Basic statistics
* Ready foundation for future modules

---

## ⚙️ Project Positioning

We DO NOT redesign the architecture.

We KEEP the original pipeline logic:

```
data → preprocessing → modeling → evaluation → integration
```

But we ADAPT:

* Medical → Legal domain
* Image-based → Text-based
* VQA → Legal QA

---

## 📦 Modules Scope

### ✅ D1 — Data Ingestion & Standardization

Role:

* Load raw data
* Convert to unified format
* Generate initial statistics

Equivalent:

```
Raw Legal Data → Unified Legal Dataset
```

---

### ✅ D2 — Preprocessing & Dataset Structuring

Role:

* Clean dataset
* Assign difficulty
* Create splits
* Final statistics

Equivalent:

```
Unified Dataset → Clean Dataset + Splits + Difficulty
```

---

## 🧠 Core Design Decisions

### 1. Task Type

👉 Legal Text Question Answering (QA)

---

### 2. Data Format

👉 JSON (chosen for flexibility and structure)

---

### 3. Unified Schema

Each sample:

```json
{
  "id": "sample_0001",
  "domain": "juridique",
  "source_dataset": "legal_qa",
  "document_id": "doc_001",
  "document_title": "Code du travail",
  "document_type": "law",
  "jurisdiction": "Morocco",
  "context": "Le contrat de travail ...",
  "question": "Quels sont les cas de rupture du contrat ?",
  "answer": "Le contrat peut être rompu dans les cas suivants ...",
  "answer_type": "extractive",
  "language": "fr",
  "difficulty": "medium",
  "split": "train",
  "metadata": {
    "article": "Art. 45",
    "topic": "contrat de travail",
    "source_file": "code_travail_001.txt"
  }
}
```

---

### 4. Data Type

We focus on:

* Legal documents (text)
* Questions
* Answers

❌ No images
❌ No complex annotations
❌ No advanced ML

---

## 🔄 Full Pipeline

### Phase A — Raw Data Collection

Sources:

* Legal texts (laws, articles)
* FAQ juridique
* Case snippets
* Manually created QA pairs

---

### Phase B — Canonical Transformation

Convert all sources into unified JSON format.

---

### Phase C — Preprocessing

Operations:

* Remove empty records
* Normalize text
* Fix encoding
* Remove duplicates
* Clean spacing
* Filter invalid entries

---

### Phase D — Difficulty Assignment

Rule-based:

* Easy → short context, direct answer
* Medium → moderate complexity
* Hard → long context, complex reasoning

---

### Phase E — Dataset Split

Default:

* 70% Train
* 15% Validation
* 15% Test

Small dataset:

* 80 / 10 / 10

---

### Phase F — Statistics

Compute:

* Total samples
* Number of documents
* Avg context length
* Avg answer length
* Distribution by split
* Distribution by difficulty
* Distribution by document type
* Language distribution

---

## 📁 Folder Structure

```bash
project/
│
├── data/
│   ├── raw/
│   ├── interim/
│   │   ├── extracted/
│   │   └── normalized/
│   ├── processed/
│   │   ├── legal_qa_dataset.json
│   │   ├── train.json
│   │   ├── val.json
│   │   ├── test.json
│   │   └── stats.json
│   └── reports/
│
├── scripts/
│   ├── 01_load_raw_data.py
│   ├── 02_convert_to_unified_format.py
│   ├── 03_clean_dataset.py
│   ├── 04_assign_difficulty.py
│   ├── 05_split_dataset.py
│   └── 06_generate_stats.py
│
├── notebooks/
├── config/
├── outputs/
├── requirements.txt
└── README.md
```

---

## 🧪 Execution Plan

### Step 1 — Define Schema

⏱️ 1–2 hours
Output: JSON structure finalized

---

### Step 2 — Collect Raw Data

⏱️ 0.5–1 day
Output: raw legal corpus

---

### Step 3 — Convert to Unified Format

⏱️ 1 day
Output:

* interim normalized JSON
* legal_qa_dataset.json

---

### Step 4 — Clean Dataset

⏱️ 0.5 day
Output: cleaned dataset

---

### Step 5 — Assign Difficulty

⏱️ 0.5 day
Output: difficulty labels

---

### Step 6 — Split Dataset

⏱️ 1–2 hours
Output:

* train.json
* val.json
* test.json

---

### Step 7 — Generate Statistics

⏱️ 0.5 day
Output:

* stats.json
* summary report

---

### Step 8 — Documentation

⏱️ 0.5 day
Output:

* README
* pipeline explanation

---

## ⏳ Estimated Timeline

* Minimum viable version: 2–3 days
* Clean structured version: 4–5 days

---

## 🧰 Tools

Minimal stack:

```txt
pandas
scikit-learn
tqdm
matplotlib
```

Optional:

```txt
numpy
seaborn
pypdf
```

---

## 🚫 What We Avoid

* Reinforcement Learning
* Federated Learning
* Complex NLP pipelines
* Multimodal processing
* Legal ontologies
* Advanced annotation
* Overengineering

---

## 📦 Final Deliverables

1. `legal_qa_dataset.json`
2. `train.json`, `val.json`, `test.json`
3. `stats.json`
4. `dataset_summary.txt`
5. `README.md`

---

## 🚀 Implementation Strategy

Start small:

1. Create 10–20 legal samples manually
2. Build pipeline on small data
3. Validate structure
4. Scale later

---

## 🧾 Final Summary

* D1 = Data ingestion + formatting
* D2 = Cleaning + splitting + difficulty
* Domain = Juridique (not medical)
* Format = JSON
* Task = Legal QA
* Approach = Simple, clean, scalable

👉 Focus: **data quality + pipeline clarity**, not complexity

---
