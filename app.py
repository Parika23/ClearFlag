from pathlib import Path
import csv, io, os
import altair as alt
import pandas as pd
import streamlit as st
from engine import DEFAULT_DB_PATH, add_case, get_case, initialise_database, list_flagged_cases, save_review
from engine import save_training_attempt
from clearflag_dataframe import ClearFlagDataFrame
from clearflag_analytics_service import ClearFlagAnalyticsService
from clearflag_insights_service import ClearFlagInsightsService, ClearFlagTrendService
from clearflag_prediction_service import ClearFlagPredictionService

st.set_page_config(page_title="ClearFlag", page_icon="🚩", layout="wide")
DB = Path(os.getenv("CLEARFLAG_DB_PATH", DEFAULT_DB_PATH)); initialise_database(DB)
def risk(level): return {"high":"🔴 High","medium":"🟠 Medium","low":"🟢 Low"}[level]
def label(cid):
    c=get_case(DB,cid); r=c["record"]
    return f"{cid} · {r.get('customer_name') or r.get('applicant_name')}"
def case_brief(case):
    r=case["record"]
    if case["case_type"] == "signup":
        return [
            f"Applicant: {r['applicant_name']} ({r['country']}).",
            f"Document resubmissions: {r['document_resubmits']}.",
            "The application name " + ("matches" if r["name_matches_document"] else "does not match") + " the identity document.",
            "The application address " + ("matches" if r["address_matches_document"] else "does not match") + " the identity document.",
            f"Device risk assessment: {r['device_risk']}."
        ]
    return [
        f"Customer: {r['customer_name']}. Transfer amount: {r['amount']:,.0f} {r['currency']}."
        "The device is " + ("new and untrusted." if r["new_device"] and not r["device_trusted"] else "recognised/trusted."),
        "This is " + ("a first payment to the beneficiary." if r["beneficiary_new"] else "not a first payment to the beneficiary.")
    ]
def show_assessment(case):
    st.success(f"Case added: {case['case_id']}")
    st.markdown(f"**Assessment:** {risk(case['risk_level'])} · **{case['suggested_action'].title()}**")
    st.write(case["reasoning"])
    if case["second_look_field"]: st.info(f"Second-look field: {case['second_look_field']}.")
def csv_template(kind):
    if kind == "transaction":
        fields = ["case_type","customer_name","amount","currency","hour","new_device","device_trusted","beneficiary_new","beneficiary","transaction_type"]
        row = ["transaction","Asha Mehta","185000","INR","2","true","false","true","New recipient","UPI"]
    else:
        fields = ["case_type","applicant_name","country","document_resubmits","name_matches_document","address_matches_document","device_risk"]
        row = ["signup","Vikram Bose","IN","3","false","false","high"]
    out = io.StringIO(); csv.writer(out).writerows([fields, row]); return out.getvalue()

st.title("ClearFlag")
st.caption("AI-assisted fraud & onboarding risk triage · Synthetic demo data only · Human review required")
page=st.sidebar.radio("View",["Analyst view","Training view","Add Case","Insights","About"])
cases=list_flagged_cases(DB)
if page == "Analyst view":
    a,b,c=st.columns(3); a.metric("Flagged cases",len(cases)); b.metric("High risk",sum(x["risk_level"]=="high" for x in cases)); c.metric("Medium risk",sum(x["risk_level"]=="medium" for x in cases))
    st.subheader("Alert queue")
    st.dataframe([{"Case":x["case_id"],"Type":x["case_type"].title(),"Subject":x.get("customer_name") or x.get("applicant_name"),"Risk":x["risk_level"].title(),"Action":x["suggested_action"].title(),"Signals":"; ".join(x["detection_reasons"]),"Review":x.get("review_decision") or "Pending"} for x in cases],hide_index=True,use_container_width=True)
    cid=st.selectbox("Open case",[x["case_id"] for x in cases],format_func=label); case=get_case(DB,cid)
    left,right=st.columns(2)
    with left:
        st.subheader(f"{cid} · {risk(case['risk_level'])}")
        st.markdown("**Case summary**\n\n" + "\n".join(f"- {line}" for line in case_brief(case)))
        with st.expander("View raw case data"):
            st.json(case["record"])
        st.markdown("**Detection signals**\n\n"+"\n".join(f"- {x}" for x in case["detection_reasons"]))
    with right:
        st.subheader("AI-assisted assessment"); st.markdown(f"**Suggested action:** {case['suggested_action'].title()}"); st.write(case["reasoning"])
        if case["second_look_field"]: st.info(f"Lightweight decision step: reviewed **{case['second_look_field']}** before finalising.")
        st.caption("Considered but not decisive: "+case["ruled_out"])
    st.subheader("Human review log")
    st.caption("Record whether you agree with the recommendation or override it. This saves to the demo's SQLite review log.")
    with st.form("review"):
        reviewer=st.text_input("Reviewed by",case.get("reviewer") or ""); decision=st.radio("Decision",["agree","override"],horizontal=True); note=st.text_area("Review note",case.get("review_note") or "")
        submitted=st.form_submit_button("Save review")
    if submitted:
        if reviewer.strip() and note.strip(): save_review(DB,cid,reviewer.strip(),decision,note.strip()); st.success("Review saved."); st.rerun()
        else: st.error("Reviewer and note are required.")
elif page == "Training view":
    cid=st.selectbox("Training case",[x["case_id"] for x in cases],format_func=label); case=get_case(DB,cid)
    if st.session_state.get("revealed_case_id") != cid:
        st.session_state.revealed = False
        st.session_state.pop("guess", None)
    st.subheader("Make your call before revealing the assessment")
    st.markdown("**Case brief**\n\n" + "\n".join(f"- {line}" for line in case_brief(case)))
    with st.expander("View raw case data"):
        st.json(case["record"])
    st.markdown("**Detection signals**\n\n"+"\n".join(f"- {x}" for x in case["detection_reasons"]))
    guess=st.radio("Your assessment",["safe","suspicious"],horizontal=True)
    if st.button("Reveal ClearFlag assessment"):
        st.session_state.revealed=True; st.session_state.guess=guess; st.session_state.revealed_case_id=cid
        save_training_attempt(DB, cid, guess, guess == "suspicious")
    if st.session_state.get("revealed"):
        (st.success if st.session_state.guess=="suspicious" else st.warning)("Match" if st.session_state.guess=="suspicious" else "Different call")
        st.markdown(f"**ClearFlag:** {risk(case['risk_level'])} · **{case['suggested_action'].title()}**"); st.write(case["reasoning"])
elif page == "Add Case":
    st.subheader("Add a case")
    st.caption("Cases are validated, assessed by the development mock, and saved to the same SQLite database as the alert queue.")
    manual_tab, upload_tab = st.tabs(["Manual entry", "CSV upload"])
    with manual_tab:
        kind = st.radio("Case type", ["Transaction", "Signup / KYC"], horizontal=True)
        with st.form("manual-case", clear_on_submit=True):
            if kind == "Transaction":
                customer_name = st.text_input("Customer name")
                amount = st.number_input("Amount", min_value=0.0, step=100.0)
                currency = st.selectbox("Currency", ["INR", "USD", "EUR"])
                hour = st.number_input("Transaction hour (0–23)", min_value=0, max_value=23, step=1)
                new_device = st.radio("New device?", ["No", "Yes"], horizontal=True)
                device_trusted = st.radio("Device trusted?", ["Yes", "No"], horizontal=True)
                beneficiary_new = st.radio("First payment to beneficiary?", ["No", "Yes"], horizontal=True)
                beneficiary = st.text_input("Beneficiary / recipient")
                transaction_type = st.selectbox("Transaction type", ["UPI", "NEFT", "RTGS", "IMPS", "Card", "Other"])
                raw = {"case_type":"transaction","customer_name":customer_name,"amount":amount,"currency":currency,"hour":hour,"new_device":new_device == "Yes","device_trusted":device_trusted == "Yes","beneficiary_new":beneficiary_new == "Yes","beneficiary":beneficiary,"transaction_type":transaction_type}
            else:
                applicant_name = st.text_input("Applicant name")
                country = st.text_input("Country code", value="IN", max_chars=2)
                document_resubmits = st.number_input("Document resubmissions", min_value=0, step=1)
                name_match = st.radio("Name matches document?", ["Yes", "No"], horizontal=True)
                address_match = st.radio("Address matches document?", ["Yes", "No"], horizontal=True)
                device_risk = st.selectbox("Device risk", ["low", "medium", "high"])
                raw = {"case_type":"signup","applicant_name":applicant_name,"country":country,"document_resubmits":document_resubmits,"name_matches_document":name_match == "Yes","address_matches_document":address_match == "Yes","device_risk":device_risk}
            submitted = st.form_submit_button("Validate and add case")
        if submitted:
            try: show_assessment(add_case(DB, raw))
            except ValueError as exc: st.error(f"Case was not added: {exc}")
            except Exception: st.error("Case could not be processed. Please check the fields and try again.")
    with upload_tab:
        st.caption("Use an explicit `case_type` column: `transaction` or `signup`. A single upload can contain either or both types.")
        st.download_button("Download transaction template CSV", csv_template("transaction"), "clearflag_transaction_template.csv", "text/csv")
        st.download_button("Download signup template CSV", csv_template("signup"), "clearflag_signup_template.csv", "text/csv")
        uploaded = st.file_uploader("Upload a CSV", type="csv")
        if uploaded and st.button("Validate and process CSV"):
            try:
                rows = list(csv.DictReader(io.StringIO(uploaded.getvalue().decode("utf-8-sig"))))
                if not rows or not rows[0]: raise ValueError("The CSV has no data rows.")
                if "case_type" not in rows[0]: raise ValueError("Missing required column: case_type")
                added, rejected = [], []
                for row_number, row in enumerate(rows, start=2):
                    try: added.append(add_case(DB, row))
                    except ValueError as exc: rejected.append(f"Row {row_number}: {exc}")
                    except Exception: rejected.append(f"Row {row_number}: could not be processed")
                flagged = sum(bool(case["detection_reasons"]) for case in added)
                st.success(f"Processed {len(added)} row(s); {flagged} flagged; {len(rejected)} rejected.")
                if rejected:
                    st.warning("Rejected rows")
                    for message in rejected: st.write(f"- {message}")
            except UnicodeDecodeError: st.error("The file must be a UTF-8 CSV.")
            except ValueError as exc: st.error(str(exc))
            except Exception: st.error("The CSV could not be read. Please check its format and try again.")
elif page == "Insights":
    st.subheader("Insights")
    st.caption("Analytics are calculated from the same SQLite cases and review records used by the rest of ClearFlag.")
    try:
        data_layer = ClearFlagDataFrame(DB)
        cases_df = data_layer.cases()
        analytics = ClearFlagAnalyticsService(cases_df)
        if not analytics.has_data:
            st.info("No cases are available for analytics yet.")
        else:
            risks = analytics.risk_level_counts; types = analytics.case_type_split; reviews = analytics.review_status_counts
            a,b,c,d = st.columns(4)
            a.metric("Total cases", analytics.total_cases)
            b.metric("Risk levels", f"H {risks['high']} · M {risks['medium']} · L {risks['low']}")
            c.metric("Case types", f"TX {types['transaction']} · KYC {types['signup']}")
            d.metric("Pending review", reviews["pending"])
            st.subheader("Operational insights")
            cards = ClearFlagInsightsService(analytics).cards()
            if cards:
                columns = st.columns(len(cards))
                for column, card in zip(columns, cards):
                    with column:
                        (st.warning if card["status"] == "warning" else st.info)(f"{card['icon']} **{card['title']}**\n\n{card['message']}")
            else: st.info("No threshold-based insights are available yet.")
            st.subheader("Detection signal frequency")
            frequencies = analytics.signal_frequency()
            if frequencies.empty: st.caption("No detection signals recorded yet.")
            else:
                signal_data = frequencies.rename_axis("signal").reset_index(name="count")
                signal_chart = alt.Chart(signal_data).mark_bar().encode(
                    y=alt.Y("signal:N", sort="-x", title=None),
                    x=alt.X("count:Q", title="Cases"),
                    tooltip=[alt.Tooltip("signal:N", title="Detection signal"), alt.Tooltip("count:Q", title="Cases")]
                ).properties(height=max(180, len(signal_data) * 34))
                st.altair_chart(signal_chart, use_container_width=True)
            attempts = data_layer.training_attempts()
            trend = ClearFlagTrendService(attempts).summary()
            if trend:
                st.subheader("Training accuracy")
                x,y,z,w = st.columns(4)
                x.metric("Accuracy", f"{trend['accuracy']}%")
                y.metric("Current streak", trend["current_streak"])
                z.metric("Best streak", trend["best_streak"])
                w.metric("Trend", trend["trend"])
            st.subheader("Rules engine vs. trained model")
            predictor = ClearFlagPredictionService(cases_df).train()
            if predictor.message: st.info(predictor.message)
            else:
                st.caption(f"Holdout accuracy: {predictor.evaluation['accuracy']}% across {predictor.evaluation['test_cases']} test case(s). Labels: {', '.join(predictor.evaluation['labels'])}.")
                labels = predictor.evaluation["labels"]  # Exact order passed to sklearn's confusion_matrix(labels=...).
                matrix_table = pd.DataFrame(predictor.evaluation["confusion_matrix"], index=[f"Actual: {label.title()}" for label in labels], columns=[f"Predicted: {label.title()}" for label in labels])
                st.caption("Confusion matrix — rows are actual risk levels; columns are model predictions.")
                st.dataframe(matrix_table, use_container_width=True)
                recent = cases_df.sort_values("date_added", ascending=False).head(5).copy()
                recent["trained_model_prediction"] = [predictor.predict(recent.iloc[[i]]) for i in range(len(recent))]
                st.dataframe(recent[["case_id","case_type","risk_level","trained_model_prediction","action"]], hide_index=True, use_container_width=True)
    except Exception:
        st.error("Insights could not be calculated right now. The core triage views remain available.")
else:
    st.subheader("One engine, two doors")
    st.write("ClearFlag chains synthetic data → validation → rules → explainable reasoning → a small second-look decision → analyst or training output. The pipeline is automated, but it is not a full autonomous agent.")
    st.info("It makes recommendations only. It does not continuously monitor accounts, share data between institutions, authenticate users, or make automatic fraud decisions.")
