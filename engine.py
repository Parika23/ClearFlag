"""ClearFlag's storage, rule detection, and explainable reasoning pipeline."""
from __future__ import annotations
import json, sqlite3, uuid
from pathlib import Path
from typing import Any
import os
from google import genai

DEFAULT_DB_PATH = Path(__file__).with_name("clearflag.db")
TRANSACTIONS = [
 {"id":"TX-001","customer_name":"Asha Mehta","amount":1250,"currency":"INR","hour":14,"new_device":False,"device_trusted":True,"beneficiary_new":False},
 {"id":"TX-002","customer_name":"Rohan Shah","amount":185000,"currency":"INR","hour":2,"new_device":True,"device_trusted":False,"beneficiary_new":True},
 {"id":"TX-003","customer_name":"Maya Iyer","amount":72000,"currency":"INR","hour":11,"new_device":False,"device_trusted":True,"beneficiary_new":True},
 {"id":"TX-004","customer_name":"Kabir Singh","amount":950,"currency":"INR","hour":9,"new_device":False,"device_trusted":True,"beneficiary_new":False},
 {"id":"TX-005","customer_name":"Nisha Rao","amount":245000,"currency":"INR","hour":23,"new_device":True,"device_trusted":False,"beneficiary_new":True},
 {"id":"TX-006","customer_name":"Arjun Patel","amount":18000,"currency":"INR","hour":4,"new_device":False,"device_trusted":True,"beneficiary_new":False},
 {"id":"TX-007","customer_name":"Zoya Khan","amount":5100,"currency":"INR","hour":17,"new_device":True,"device_trusted":False,"beneficiary_new":False},
 {"id":"TX-008","customer_name":"Dev Malhotra","amount":310000,"currency":"INR","hour":13,"new_device":False,"device_trusted":True,"beneficiary_new":False}]
SIGNUPS = [
 {"id":"KYC-001","applicant_name":"Ishita Sen","country":"IN","document_resubmits":0,"name_matches_document":True,"address_matches_document":True,"device_risk":"low"},
 {"id":"KYC-002","applicant_name":"Vikram Bose","country":"IN","document_resubmits":3,"name_matches_document":False,"address_matches_document":False,"device_risk":"high"},
 {"id":"KYC-003","applicant_name":"Leena Das","country":"IN","document_resubmits":1,"name_matches_document":True,"address_matches_document":False,"device_risk":"medium"},
 {"id":"KYC-004","applicant_name":"Sameer Ali","country":"IN","document_resubmits":0,"name_matches_document":True,"address_matches_document":True,"device_risk":"low"},
 {"id":"KYC-005","applicant_name":"Priya Nair","country":"AE","document_resubmits":2,"name_matches_document":True,"address_matches_document":False,"device_risk":"high"},
 {"id":"KYC-006","applicant_name":"Aditya Roy","country":"IN","document_resubmits":0,"name_matches_document":False,"address_matches_document":True,"device_risk":"low"},
 {"id":"KYC-007","applicant_name":"Fatima Noor","country":"IN","document_resubmits":4,"name_matches_document":False,"address_matches_document":False,"device_risk":"high"},
 {"id":"KYC-008","applicant_name":"Karan Jain","country":"IN","document_resubmits":0,"name_matches_document":True,"address_matches_document":True,"device_risk":"low"}]
TRANSACTIONS.extend([
 {"id":"TX-009","customer_name":"Neel Verma","amount":2200,"currency":"INR","hour":10,"new_device":False,"device_trusted":True,"beneficiary_new":False},
 {"id":"TX-010","customer_name":"Tara Kapoor","amount":158000,"currency":"INR","hour":15,"new_device":False,"device_trusted":True,"beneficiary_new":True},
 {"id":"TX-011","customer_name":"Om Prakash","amount":3400,"currency":"INR","hour":22,"new_device":False,"device_trusted":True,"beneficiary_new":False},
 {"id":"TX-012","customer_name":"Riya Sethi","amount":49000,"currency":"INR","hour":3,"new_device":True,"device_trusted":False,"beneficiary_new":False},
 {"id":"TX-013","customer_name":"Jay Arora","amount":8900,"currency":"INR","hour":12,"new_device":False,"device_trusted":True,"beneficiary_new":False},
 {"id":"TX-014","customer_name":"Sana Mir","amount":215000,"currency":"INR","hour":1,"new_device":True,"device_trusted":False,"beneficiary_new":True},
 {"id":"TX-015","customer_name":"Manav Kohli","amount":12000,"currency":"INR","hour":16,"new_device":False,"device_trusted":True,"beneficiary_new":True},
 {"id":"TX-016","customer_name":"Anika Gupta","amount":650,"currency":"INR","hour":8,"new_device":False,"device_trusted":True,"beneficiary_new":False}])
SIGNUPS.extend([
 {"id":"KYC-009","applicant_name":"Naveen Paul","country":"IN","document_resubmits":0,"name_matches_document":True,"address_matches_document":True,"device_risk":"low"},
 {"id":"KYC-010","applicant_name":"Meera Joshi","country":"IN","document_resubmits":2,"name_matches_document":True,"address_matches_document":True,"device_risk":"medium"},
 {"id":"KYC-011","applicant_name":"Ritesh Bhat","country":"IN","document_resubmits":0,"name_matches_document":False,"address_matches_document":True,"device_risk":"medium"},
 {"id":"KYC-012","applicant_name":"Anya Dutta","country":"IN","document_resubmits":3,"name_matches_document":False,"address_matches_document":False,"device_risk":"high"},
 {"id":"KYC-013","applicant_name":"Himanshu Lal","country":"IN","document_resubmits":0,"name_matches_document":True,"address_matches_document":True,"device_risk":"low"},
 {"id":"KYC-014","applicant_name":"Saira Khan","country":"AE","document_resubmits":2,"name_matches_document":True,"address_matches_document":False,"device_risk":"high"},
 {"id":"KYC-015","applicant_name":"Aman Kapoor","country":"IN","document_resubmits":1,"name_matches_document":True,"address_matches_document":True,"device_risk":"low"},
 {"id":"KYC-016","applicant_name":"Diya Bose","country":"IN","document_resubmits":0,"name_matches_document":True,"address_matches_document":True,"device_risk":"low"}])

def validate(r: dict[str, Any], kind: str) -> list[str]:
    fields = ["id","customer_name","amount","hour","new_device","device_trusted"] if kind == "transaction" else ["id","applicant_name","document_resubmits","name_matches_document","address_matches_document","device_risk"]
    errors = [f"Missing {f}" for f in fields if r.get(f) is None or r.get(f) == ""]
    if kind == "transaction" and (not isinstance(r.get("amount"), (int,float)) or isinstance(r.get("amount"), bool)): errors.append("Amount must be numeric")
    if kind == "transaction" and (not isinstance(r.get("hour"), int) or not 0 <= r["hour"] <= 23): errors.append("Hour must be an integer from 0 to 23")
    if kind == "signup" and (not isinstance(r.get("document_resubmits"), int) or r["document_resubmits"] < 0): errors.append("document_resubmits must be a non-negative integer")
    if kind == "signup" and r.get("device_risk") not in {"low", "medium", "high"}: errors.append("device_risk must be low, medium, or high")
    return errors

def detect(r: dict[str, Any], kind: str) -> list[str]:
    invalid = validate(r, kind)
    if invalid: return ["Malformed record: " + "; ".join(invalid)]
    s = []
    if kind == "transaction":
        if r["amount"] >= 150000: s.append("Unusually large transfer amount")
        if r["hour"] < 6 or r["hour"] >= 23: s.append("Transaction at an unusual hour")
        if r["new_device"] and not r["device_trusted"]: s.append("New, untrusted device")
        if r.get("beneficiary_new"): s.append("First payment to this beneficiary")
    else:
        if r["document_resubmits"] >= 2: s.append("Multiple document resubmissions")
        if not r["name_matches_document"]: s.append("Applicant name does not match document")
        if not r["address_matches_document"]: s.append("Address does not match document")
        if r["device_risk"] == "high": s.append("High-risk signup device")
    return s

def _fallback(r: dict[str,Any], kind: str, signals: list[str]) -> dict[str, str|None]:
    risk = "high" if len(signals) >= 3 or any("Malformed" in x for x in signals) else "medium" if len(signals) >= 2 else "low"
    action = {"high":"block", "medium":"watch", "low":"approve"}[risk]
    field = ("device trust and beneficiary history" if kind == "transaction" and (r.get("new_device") or r.get("beneficiary_new")) else "document-to-application consistency" if kind == "signup" and (not r.get("name_matches_document") or r.get("document_resubmits",0)>=2) else None)
    who = r.get("customer_name") or r.get("applicant_name") or "This case"
    why = ", ".join(x.lower() for x in signals) if signals else "no risk signals that meet the demo rules"
    return {"risk_level":risk,"suggested_action":action,"reasoning":f"{who}'s case is {risk} risk because the detection layer found {why}.","second_look_field":field,"ruled_out":"A single unusual signal can be legitimate; the combined pattern drives this recommendation."}
def reason(r: dict[str,Any], kind: str, signals: list[str]) -> dict[str,str|None]:
    """Generate an AI-assisted explanation using Gemini."""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            api_key = None
    if not api_key:
        return _fallback(r, kind, signals)

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
You are the AI-assisted reasoning component of ClearFlag,
a demonstration fraud and KYC risk assessment system.

The deterministic rules engine has already detected the risk signals.

Your job is to:
- explain the detected signals,
- provide concise reasoning,
- identify what a human reviewer should check,
- recommend an appropriate next step.

Do not invent facts.
Do not invent customer information.
Do not make the final compliance decision.
Do not ignore the supplied risk signals.

CASE TYPE:
{kind}

CASE DATA:
{json.dumps(r, indent=2, default=str)}

DETECTED RISK SIGNALS:
{json.dumps(signals, indent=2, default=str)}

Return ONLY valid JSON with exactly these fields:

{{
    "risk_level": "low",
    "suggested_action": "approve",
    "reasoning": "Concise explanation of the detected risk.",
    "second_look_field": "The main thing a human reviewer should verify.",
    "ruled_out": "Something that should not automatically be assumed."
}}

Use only:
risk_level = low, medium, or high
suggested_action = approve, watch, or block

Keep the response concise.
"""

        response = client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt,
        )

        text = response.text.strip()

        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        result = json.loads(text)

        required_fields = {
            "risk_level",
            "suggested_action",
            "reasoning",
            "second_look_field",
            "ruled_out",
        }

        if not required_fields.issubset(result):
            raise ValueError("Gemini response is missing required fields.")

        if result["risk_level"] not in {"low", "medium", "high"}:
            raise ValueError("Invalid risk level returned by Gemini.")

        if result["suggested_action"] not in {"approve", "watch", "block"}:
            raise ValueError("Invalid suggested action returned by Gemini.")

        return {
            "risk_level": result["risk_level"],
            "suggested_action": result["suggested_action"],
            "reasoning": result["reasoning"],
            "second_look_field": result["second_look_field"],
            "ruled_out": result["ruled_out"],
        }

    except Exception as exc:
        print(f"Gemini reasoning error: {exc}")
        return _fallback(r, kind, signals)

def _as_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool): return value
    if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1"}: return True
    if isinstance(value, str) and value.strip().lower() in {"false", "no", "0"}: return False
    raise ValueError(f"{field} must be true or false")

def normalise_case(raw: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """CSV uses explicit case_type so mixed uploads stay unambiguous."""
    kind = str(raw.get("case_type", "")).strip().lower()
    if kind not in {"transaction", "signup"}: raise ValueError("case_type must be transaction or signup")
    required = (["customer_name", "amount", "hour", "new_device", "device_trusted", "beneficiary_new"] if kind == "transaction" else ["applicant_name", "country", "document_resubmits", "name_matches_document", "address_matches_document", "device_risk"])
    missing = [field for field in required if raw.get(field) is None or str(raw.get(field)).strip() == ""]
    if missing: raise ValueError(f"Missing required field: {missing[0]}")
    try:
        if kind == "transaction":
            record = {"id": str(raw.get("id") or f"TX-{uuid.uuid4().hex[:8].upper()}"), "customer_name": str(raw.get("customer_name", "")).strip(), "amount": float(raw.get("amount")), "currency": str(raw.get("currency") or "INR").upper(), "hour": int(raw.get("hour")), "new_device": _as_bool(raw.get("new_device"), "new_device"), "device_trusted": _as_bool(raw.get("device_trusted"), "device_trusted"), "beneficiary_new": _as_bool(raw.get("beneficiary_new"), "beneficiary_new"), "beneficiary": str(raw.get("beneficiary") or "").strip(), "transaction_type": str(raw.get("transaction_type") or "").strip()}
        else:
            record = {"id": str(raw.get("id") or f"KYC-{uuid.uuid4().hex[:8].upper()}"), "applicant_name": str(raw.get("applicant_name", "")).strip(), "country": str(raw.get("country", "")).upper().strip(), "document_resubmits": int(raw.get("document_resubmits")), "name_matches_document": _as_bool(raw.get("name_matches_document"), "name_matches_document"), "address_matches_document": _as_bool(raw.get("address_matches_document"), "address_matches_document"), "device_risk": str(raw.get("device_risk", "")).lower().strip()}
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc
    errors = validate(record, kind)
    if errors: raise ValueError("; ".join(errors))
    return record, kind

def add_case(db: Path, raw: dict[str, Any]) -> dict[str, Any]:
    """Validate, detect, mock-reason, and persist one manually added/imported case."""
    record, kind = normalise_case(raw)
    signals = detect(record, kind)
    assessment = reason(record, kind, signals)
    try:
        with sqlite3.connect(db) as c:
            c.execute("INSERT INTO cases(case_id,case_type,record_json,detection_json,risk_level,suggested_action,reasoning,second_look_field,ruled_out) VALUES(?,?,?,?,?,?,?,?,?)", (record["id"], kind, json.dumps(record), json.dumps(signals), *assessment.values()))
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Duplicate case ID: {record['id']}") from exc
    return get_case(db, record["id"])

def initialise_database(db: Path=DEFAULT_DB_PATH) -> None:
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE IF NOT EXISTS cases(case_id TEXT PRIMARY KEY, case_type TEXT, record_json TEXT, detection_json TEXT, risk_level TEXT, suggested_action TEXT, reasoning TEXT, second_look_field TEXT, ruled_out TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS reviews(case_id TEXT PRIMARY KEY, reviewer TEXT, decision TEXT CHECK(decision IN ('agree','override')), note TEXT, reviewed_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS training_attempts(attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, guess TEXT NOT NULL CHECK(guess IN ('safe','suspicious')), matched INTEGER NOT NULL, attempted_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        columns = {row[1] for row in c.execute("PRAGMA table_info(cases)")}
        if "created_at" not in columns: c.execute("ALTER TABLE cases ADD COLUMN created_at TEXT")
        c.execute("UPDATE cases SET created_at=COALESCE(created_at, CURRENT_TIMESTAMP)")
        if c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]: return
        for kind, records in (("transaction",TRANSACTIONS),("signup",SIGNUPS)):
            for r in records:
                signals=detect(r,kind)
                if signals:
                    a=reason(r,kind,signals)
                    c.execute("INSERT INTO cases(case_id,case_type,record_json,detection_json,risk_level,suggested_action,reasoning,second_look_field,ruled_out) VALUES(?,?,?,?,?,?,?,?,?)",(r["id"],kind,json.dumps(r),json.dumps(signals),*a.values()))

def _case(row: sqlite3.Row) -> dict[str,Any]:
    d=dict(row); d["record"]=json.loads(d.pop("record_json")); d["detection_reasons"]=json.loads(d.pop("detection_json")); d.update(d["record"]); return d
def list_flagged_cases(db: Path=DEFAULT_DB_PATH) -> list[dict[str,Any]]:
    with sqlite3.connect(db) as c:
        c.row_factory=sqlite3.Row
        rows=c.execute("SELECT c.*,r.reviewer,r.decision review_decision,r.note review_note FROM cases c LEFT JOIN reviews r USING(case_id) ORDER BY CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,case_id").fetchall()
    return [_case(x) for x in rows]
def get_case(db: Path, cid: str) -> dict[str,Any]: return next(x for x in list_flagged_cases(db) if x["case_id"]==cid)
def save_review(db: Path,cid:str,reviewer:str,decision:str,note:str) -> None:
    if decision not in {"agree","override"}: raise ValueError("Invalid decision")
    with sqlite3.connect(db) as c: c.execute("INSERT INTO reviews(case_id,reviewer,decision,note) VALUES(?,?,?,?) ON CONFLICT(case_id) DO UPDATE SET reviewer=excluded.reviewer,decision=excluded.decision,note=excluded.note,reviewed_at=CURRENT_TIMESTAMP",(cid,reviewer,decision,note))
def save_training_attempt(db: Path, cid: str, guess: str, matched: bool) -> None:
    if guess not in {"safe", "suspicious"}: raise ValueError("Invalid training guess")
    with sqlite3.connect(db) as c: c.execute("INSERT INTO training_attempts(case_id,guess,matched) VALUES(?,?,?)", (cid, guess, int(matched)))
