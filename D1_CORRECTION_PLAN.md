# 🔧 D1 CORRECTION PLAN — Legal Dataset Pipeline

## 🎯 OBJECTIVE

Refine and correct the existing implementation to strictly match **D1 requirements** from MMedAgent-Lite.

⚠️ IMPORTANT:

* DO NOT rebuild from scratch
* MODIFY existing outputs only
* FOCUS on data understanding and statistics

---

## ✅ CURRENT STATE (FROM PREVIOUS WORK)

The pipeline already includes:

* Cleaned dataset ✔
* JSON format ✔
* Filtering ✔
* Basic statistics ✔
* Splits ✔ (extra, not required but allowed)
* Difficulty ✔ (optional)

---

## ❌ PROBLEM

The current pipeline behaves like **D1 + D2**, while we only need:

👉 **D1 = Data + Pipeline + Analysis**

Missing critical component:

👉 **DATA ANALYSIS**

---

## 🧠 REQUIRED CORRECTIONS

### 1. KEEP (DO NOT CHANGE)

* dataset structure
* cleaning logic
* JSON output
* filtering rules

---

### 2. IGNORE (OPTIONAL)

You may ignore:

* difficulty
* train/val/test split

(keep them but do not focus on them)

---

### 3. ADD — DATA ANALYSIS (CRITICAL)

You MUST generate a new section:

## 📊 DATA ANALYSIS

### A. Question Types Analysis

Classify questions into categories (rule-based):

* definition
* condition
* procedure
* obligation
* other

Output:

* distribution (%)

---

### B. Length Analysis

Compute:

* question length (words)
* answer length (words)
* context length (words)

Output:

* averages
* min / max

---

### C. Answer Type

Classify answers:

* short (≤ 5 words)
* medium (6–15)
* long (>15)

Output:

* distribution

---

### D. Dataset Filtering Impact

Report:

* initial size
* after language filtering
* after extractive filtering
* final size

---

### E. Sample Examples

Provide:

* 5 real samples from dataset
* show:

  * question
  * context
  * answer

---

## 📁 OUTPUT FILES

Update / create:

* `analysis.json`
* update `REPORT.md`

---

## 🧾 REPORT UPDATE

Add new section:

## DATA ANALYSIS

Include:

* all metrics above
* interpretation (simple)

---

## ⚠️ CONSTRAINTS

* NO ML
* NO complexity
* RULE-BASED only
* CLEAR and readable outputs

---

## ✅ FINAL GOAL

Deliver:

* Improved REPORT.md
* Clear dataset analysis
* Same dataset (no rebuild)

---

## 🚀 EXECUTION

1. Load existing processed dataset
2. Compute analysis
3. Update REPORT.md
4. Save analysis.json

DO NOT redo preprocessing pipeline
