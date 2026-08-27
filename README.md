# 🚩 ClearFlag

**An AI-assisted fraud & onboarding-risk triage assistant — with a training mode built in.**

ClearFlag is a demo scale system that flags suspicious transactions and risky account sign ups, explains *why* in plain language, and routes them to a human for the final call. The same reasoning engine also powers a training mode, so new analysts can practice spotting risk on realistic cases before touching the real queue.

🔗 **Try the live app → https://clearflag.streamlit.app/**

> Runs entirely on synthetic data. No real customers, transactions, or documents are involved.

---

## What it does

ClearFlag has one reasoning engine behind two doors:

| | Analyst View | Training View |
|---|---|---|
| **Who it's for** | Someone reviewing real flagged cases | Someone learning to spot fraud/risk signals |
| **What they see** | Full case detail + AI assessment + review log | The case only — they guess the risk level first |
| **Outcome** | Agree or override, with a note (audit trail) | Instant feedback, streak tracking, accuracy trend |

Both views run the exact same detection and reasoning pipeline underneath — one engine, two experiences.

### Core features

- **🔍 Rule-based fraud & KYC detection** — transparent, explainable signals (new/untrusted device, first-time beneficiary, document mismatches, repeated resubmissions, high device risk, etc.), not a black box.
- **🤖 AI-assisted reasoning** — each flagged case is sent to Google's **Gemini** along with the detected signals, and returns a plain language explanation, a suggested action, and a "second look" field for the human reviewer. If no API key is configured, ClearFlag falls back to a deterministic, still explainable rules based summary — so the app always works, with or without a live key.
- **🎯 Training mode** — trainees guess the risk level on real (synthetic) cases, then see the correct answer with reasoning. Streaks and accuracy trends are tracked over time.
- **➕ Add cases two ways** — manual entry, or bulk CSV upload (with per row validation, so one bad row doesn't kill the batch).
- **📊 Insights dashboard** — case volume, risk mix, most common signals, review backlog, training accuracy/streaks, and a small **decision-tree classifier** trained on the flagged cases as a sanity check against the transparent rules.
- **📝 Human-in-the-loop review log** — every analyst decision (agree / override + note) is saved, so there's a record of human oversight, not just AI output.

---

## Tech stack

- **Python + [Streamlit](https://streamlit.io/)** — UI and app framework
- **SQLite** — case storage (zero setup, file-based)
- **Google Gemini API** (`google-genai`) — the AI reasoning layer, with a deterministic fallback
- **pandas** — data prep for analytics and model training
- **scikit-learn** — `DecisionTreeClassifier` for the model comparison view, evaluated with accuracy + a confusion matrix (this is a *classification* task, not regression)
- **Altair** — charts in the Insights view

---

## Run it locally

```bash
git clone <this-repo-url>
cd ClearFlag
python -m pip install -r requirements.txt
streamlit run app.py
```

The app creates its SQLite database automatically on first run — no setup required.

### (Optional) Enable live AI reasoning

Without a key, ClearFlag still works — it uses a deterministic fallback that produces explainable, rules based assessments. To get live Gemini generated reasoning instead, set an API key:

```bash
# Option 1: environment variable
export GEMINI_API_KEY=your_key_here

# Option 2: Streamlit secrets (secrets.toml)
GEMINI_API_KEY = "your_key_here"
```

Never commit an API key to source control — always read it from an environment variable or Streamlit secret.

---

## Adding cases

The **Add Case** view supports manual entry and CSV upload. CSVs use an explicit `case_type` column (`transaction` or `signup`) so mixed uploads are unambiguous, and invalid rows are reported without blocking the rest of the batch.

**Transaction CSV columns:**
`case_type, customer_name, amount, currency, hour, new_device, device_trusted, beneficiary_new, beneficiary, transaction_type`

**Signup CSV columns:**
`case_type, applicant_name, country, document_resubmits, name_matches_document, address_matches_document, device_risk`

---

## How it works, end to end

```
Data in (manual / CSV)
     │
     ▼
Validation  →  rejects malformed rows, keeps the rest usable
     │
     ▼
Rule-based detection  →  transparent, explainable signals
     │
     ▼
AI reasoning (Gemini, with deterministic fallback)  →  risk level, suggested action, plain language rationale, "second look" field
     │
     ▼
Analyst view (human review + audit log)   or   Training view (guess → feedback)
```

The "second look" field is intentionally lightweight — a nudge toward what a reviewer should double check, not an autonomous decision. ClearFlag never independently gathers data, investigates, or makes a final call; a human always does.

---

## Insights & model comparison

The Insights view is layered so each piece has one job:

- `ClearFlagDataFrame` — turns stored SQLite cases into a pandas dataframe
- `ClearFlagAnalyticsService` — counts, risk mix, signal frequency
- `ClearFlagInsightsService` — threshold-based summary cards (e.g. "30%+ of cases are high risk")
- `ClearFlagTrendService` — training accuracy and streaks
- `ClearFlagPredictionService` — trains a small `DecisionTreeClassifier` on flagged cases for comparison against the transparent rules

Model features: `amount`, `transaction_hour`, `new_device`, `device_trusted`, `beneficiary_new`, `document_resubmits`, `name_matches_document`, `address_matches_document`, `device_risk_code`, `is_transaction`. Since risk level is categorical, this is evaluated as a classification problem — accuracy and a confusion matrix, not MAE/R².

---

## Scope & limitations (by design)

This is a learning focused proof of concept, not a production fraud system. It intentionally does **not** do:

- Continuous transaction monitoring
- Cross-institution data sharing
- Identity verification
- Autonomous payment or account decisions
- Authentication / role based access control (not yet built — see below)

### What a real deployment would still need

- A documented lawful basis for data use, retention schedules, encryption, access control, and audit logs
- Defined human-review, escalation, and override procedures
- Model validation: false-positive/negative costs, calibration, drift monitoring, bias testing across relevant groups, and independent governance sign-off
- If moving from rules to ML: labelled historical data, leakage testing, reproducible training, and change control
- If extended to a multi step agent: strict tool permissions, bounded steps, per-step audit logs, and mandatory human approval for consequential actions

## Planned improvements
- Authentication and role-based access control
- Managed database, backups, and operational monitoring
- A bounded multi step investigation agent with human approval gates

## Project structure

```
ClearFlag/
├── app.py                          # Streamlit UI — Analyst, Training, Add Case, Insights views
├── engine.py                       # Storage, validation, rule detection, AI reasoning (+ fallback)
├── clearflag_dataframe.py          # SQLite → pandas conversion
├── clearflag_analytics_service.py  # Counts, risk mix, signal frequency
├── clearflag_insights_service.py   # Summary cards + training trend/streak logic
├── clearflag_prediction_service.py # Decision-tree classifier for model comparison
├── test_engine.py                  # Tests for the core engine
└── requirements.txt
```

---

## Why this project exists

ClearFlag was built to demonstrate the same architectural pattern — validation → rule-based detection → ML/AI-assisted reasoning → human reviewed output — applied to a fraud/KYC domain, deliberately mirroring the service layer structure used in my other project, [FlowState](#), for consistency across a portfolio. It touches AI/LLM integration, applied ML, and banking/fintech risk concepts in one small, explainable, honestly scoped app.
