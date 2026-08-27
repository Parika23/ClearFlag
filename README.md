# ClearFlag

ClearFlag is a demo-scale fraud and onboarding-risk assistant. A shared reasoning engine powers two interfaces: an analyst alert queue and a case-based training exercise. It uses synthetic data only and gives explainable recommendations for human review.

## Run locally

```powershell
cd ClearFlag
python -m pip install -r requirements.txt
streamlit run app.py
```

The application creates `clearflag.db` automatically. During development, the reasoning layer is deliberately mocked: it produces deterministic, explainable assessments without calling an API or requiring an API key. `engine.reason(record, kind, signals)` is the single integration boundary; it contains a `TODO` for replacing the mock with a real, structured LLM call at deployment. Read any future key from an environment variable or Streamlit secret—never from source code.

## Add cases

The **Add Case** view supports manual entry and CSV upload. CSV uses an explicit `case_type` column (`transaction` or `signup`) so mixed uploads are unambiguous. Valid cases are persisted to the same SQLite database and appear in the Analyst queue; invalid rows are reported without stopping the rest of the upload.

Transaction CSV columns: `case_type`, `customer_name`, `amount`, `currency`, `hour`, `new_device`, `device_trusted`, `beneficiary_new`, `beneficiary`, `transaction_type`.

Signup CSV columns: `case_type`, `applicant_name`, `country`, `document_resubmits`, `name_matches_document`, `address_matches_document`, `device_risk`.

## Insights and model comparison

The Insights view follows a layered design: `ClearFlagDataFrame` prepares SQLite records as a pandas dataframe; `ClearFlagAnalyticsService` calculates counts and signal frequencies; `ClearFlagInsightsService` produces threshold-based cards; `ClearFlagTrendService` calculates training accuracy and streaks; and `ClearFlagPredictionService` trains a small decision-tree classifier for comparison with the transparent rules.

The model features are `amount`, `transaction_hour`, `new_device`, `device_trusted`, `beneficiary_new`, `document_resubmits`, `name_matches_document`, `address_matches_document`, `device_risk_code`, and `is_transaction`. Risk level is categorical, so this is a classification task and is evaluated with accuracy and a confusion matrix—not regression metrics such as MAE or R².

## How it works

Synthetic transaction and KYC records are stored in SQLite. A validation layer prevents malformed data from crashing the pipeline. Explainable rules flag suspicious cases; the reasoning layer produces risk, action, a plain-language rationale, and—where appropriate—a limited second-look field. The result appears in the analyst view or training view. A typed review log illustrates human oversight.

## Automation and agentic behaviour

The pipeline is automated end-to-end: data → validation → detection → reasoning → decision step → output. The second-look field is lightweight agentic behaviour, not a full autonomous agent: ClearFlag does not independently gather data, run open-ended investigations, or make final decisions.

## Production notes

A real deployment would require a documented lawful basis for data use, purpose limitation, retention schedules, encryption, access control, audit logs, and clear customer notices or consent where applicable. Recommendations must have defined human-review, escalation, override, and quality-sampling procedures.

Model validation should cover false-positive and false-negative costs, calibration, performance by product and cohort, drift, prompt injection, versioned evaluations, rollback, and independent governance approval. Bias testing should assess error rates and outcomes across legally appropriate groups or proxies, with remediation and sign-off where material differences are found.

Moving from rules to ML requires labelled historical data, data-quality controls, leakage testing, reproducible training, explainability, monitoring, and change control. A future multi-step agent needs strict tool permissions, bounded steps, stop conditions, per-step audit logs, and mandatory human approval for consequential actions.

## Future improvements

- Authentication and role-based access control.
- Red-team testing for adversarial form content, prompt injection, and rule evasion.
- Managed database, backups, encryption, and operational monitoring.
- A bounded multi-step investigation agent with human approval gates.

## Scope boundary

This learning proof of concept is not a production fraud system. It does not do continuous monitoring, cross-institution data sharing, identity verification, or autonomous payment/account decisions.
