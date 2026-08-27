"""Small supervised classification service for comparison with transparent rules."""
from __future__ import annotations
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier


class ClearFlagPredictionService:
    FEATURE_COLUMNS = ["amount","transaction_hour","new_device","device_trusted","beneficiary_new","document_resubmits","name_matches_document","address_matches_document","device_risk_code","is_transaction"]
    TARGET_COLUMN = "risk_level"
    def __init__(self, dataframe: pd.DataFrame): self.dataframe=dataframe; self.model=None; self.evaluation=None; self.message=None
    def _features(self, frame):
        data = frame.copy(); data["device_risk_code"] = data["device_risk"].map({"low":0,"medium":1,"high":2}).fillna(0)
        return data[self.FEATURE_COLUMNS].fillna(0)
    def train(self):
        if len(self.dataframe) < 12:
            self.message = "Not enough data to train a model yet (need at least 12 cases)."; return self
        labels = self.dataframe[self.TARGET_COLUMN]
        if labels.nunique() < 2:
            self.message = "Not enough risk-level variety to train a model yet."; return self
        features = self._features(self.dataframe)
        try:
            stratify = labels if labels.value_counts().min() >= 2 else None
            x_train,x_test,y_train,y_test = train_test_split(features,labels,test_size=.30,random_state=42,stratify=stratify)
            # Risk level is categorical, so this is classification—not FlowState-style
            # regression. Accuracy and a confusion matrix replace MAE and R².
            self.model = DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=42)
            self.model.fit(x_train,y_train); prediction=self.model.predict(x_test)
            labels_seen=sorted(labels.unique())
            self.evaluation={"accuracy":round(accuracy_score(y_test,prediction)*100,1),"confusion_matrix":confusion_matrix(y_test,prediction,labels=labels_seen).tolist(),"labels":labels_seen,"test_cases":len(y_test)}
        except ValueError:
            self.message = "Not enough balanced case data to create a train/test split yet."
        return self
    def predict(self, case_frame):
        if self.model is None: return None
        return self.model.predict(self._features(case_frame))[0]
