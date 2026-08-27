"""Calculation layer only; interpretation belongs in ClearFlagInsightsService."""
from __future__ import annotations
import pandas as pd


class ClearFlagAnalyticsService:
    def __init__(self, dataframe: pd.DataFrame): self.dataframe = dataframe
    @property
    def has_data(self): return not self.dataframe.empty
    @property
    def total_cases(self): return len(self.dataframe)
    @property
    def risk_level_counts(self): return self.dataframe["risk_level"].value_counts().reindex(["low","medium","high"], fill_value=0).to_dict() if self.has_data else {"low":0,"medium":0,"high":0}
    @property
    def case_type_split(self): return self.dataframe["case_type"].value_counts().reindex(["transaction","signup"], fill_value=0).to_dict() if self.has_data else {"transaction":0,"signup":0}
    @property
    def review_status_counts(self): return self.dataframe["review_status"].value_counts().reindex(["pending","reviewed"], fill_value=0).to_dict() if self.has_data else {"pending":0,"reviewed":0}
    def signal_frequency(self):
        if not self.has_data: return pd.Series(dtype="int64")
        return self.dataframe.explode("detection_signals")["detection_signals"].dropna().loc[lambda s: s != ""].value_counts()
