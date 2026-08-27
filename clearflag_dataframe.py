"""Data-preparation layer only: SQLite records become analytics-ready DataFrames."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
import pandas as pd


class ClearFlagDataFrame:
    def __init__(self, db_path: Path): self.db_path = db_path

    def cases(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""SELECT c.case_id,c.case_type,c.record_json,c.detection_json,c.risk_level,
                c.suggested_action,c.created_at,r.decision AS review_decision
                FROM cases c LEFT JOIN reviews r ON c.case_id=r.case_id""").fetchall()
        prepared = []
        for case_id, case_type, record_json, signals_json, risk_level, action, created_at, review in rows:
            record = json.loads(record_json)
            prepared.append({"case_id":case_id, "case_type":case_type, "risk_level":risk_level,
                "action":action, "detection_signals":json.loads(signals_json),
                "review_status":"reviewed" if review else "pending", "date_added":created_at,
                "amount":record.get("amount", 0), "transaction_hour":record.get("hour", 0),
                "new_device":int(bool(record.get("new_device", False))), "device_trusted":int(bool(record.get("device_trusted", False))),
                "beneficiary_new":int(bool(record.get("beneficiary_new", False))),
                "document_resubmits":record.get("document_resubmits", 0),
                "name_matches_document":int(bool(record.get("name_matches_document", True))),
                "address_matches_document":int(bool(record.get("address_matches_document", True))),
                "device_risk":record.get("device_risk", "low"), "is_transaction":int(case_type == "transaction")})
        columns = ["case_id","case_type","risk_level","action","detection_signals","review_status","date_added","amount","transaction_hour","new_device","device_trusted","beneficiary_new","document_resubmits","name_matches_document","address_matches_document","device_risk","is_transaction"]
        return pd.DataFrame(prepared, columns=columns)

    def training_attempts(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT case_id,guess,matched,attempted_at FROM training_attempts ORDER BY attempt_id").fetchall()
        return pd.DataFrame(rows, columns=["case_id","guess","matched","attempted_at"])
