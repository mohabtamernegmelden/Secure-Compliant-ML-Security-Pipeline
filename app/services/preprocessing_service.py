import json
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.services.logging_service import app_logger


class PreprocessingService:
    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parents[2]
        models_dir = Path(os.getenv("MODEL_DIR", base_dir / "models"))
        if not models_dir.exists():
            fallback_dir = Path.cwd() / "models"
            if fallback_dir.exists():
                models_dir = fallback_dir

        self.feature_config: dict[str, Any] | None = None
        self.num_features: list[str] = []
        self.cat_features: list[str] = []
        self.model_feature_order: list[str] = []
        self.scaler = None
        self.encoder = None
        self.configured = False
        self.amount_threshold = 0.0

        globals()["feature_config"] = self.feature_config
        globals()["num_features"] = self.num_features
        globals()["cat_features"] = self.cat_features
        globals()["model_feature_order"] = self.model_feature_order
        globals()["scaler"] = self.scaler
        globals()["encoder"] = self.encoder
        globals()["configured"] = self.configured

        config_path = models_dir / "feature_columns.json"
        if not config_path.exists():
            app_logger.warning("Feature columns config not found; preprocessing is disabled")
            return

        with config_path.open("r", encoding="utf-8") as handle:
            self.feature_config = json.load(handle)

        self.num_features = self.feature_config.get("numerical_features", [])
        self.cat_features = self.feature_config.get("categorical_features", [])

        self.load_ensemble_metadata(models_dir)
        self.load_model_artifacts(models_dir)
        self.compute_amount_threshold()

        self.configured = bool(self.feature_config and self.model_feature_order)
        globals()["feature_config"] = self.feature_config
        globals()["num_features"] = self.num_features
        globals()["cat_features"] = self.cat_features
        globals()["model_feature_order"] = self.model_feature_order
        globals()["scaler"] = self.scaler
        globals()["encoder"] = self.encoder
        globals()["configured"] = self.configured
        app_logger.info("Preprocessing service initialized")

    def load_ensemble_metadata(self, models_dir: Path) -> None:
        metadata_path = models_dir / "ensemble_metadata.json"
        if not metadata_path.exists():
            app_logger.warning("Ensemble metadata not found; cannot infer model feature order")
            return

        try:
            with metadata_path.open("r", encoding="utf-8") as handle:
                metadata = json.load(handle)
            self.model_feature_order = metadata.get("features", [])
            app_logger.info("Loaded model feature order from ensemble metadata: %s", self.model_feature_order)
        except Exception as exc:  # pragma: no cover
            app_logger.exception("Failed to load ensemble metadata: %s", exc)

    def load_model_artifacts(self, models_dir: Path) -> None:
        scaler_path = models_dir / "scaler.pkl"
        if scaler_path.exists():
            try:
                self.scaler = joblib.load(scaler_path)
            except Exception as exc:  # pragma: no cover
                app_logger.exception("Failed to load scaler artifact: %s", exc)

        encoder_path = models_dir / "encoder.pkl"
        if encoder_path.exists():
            try:
                self.encoder = joblib.load(encoder_path)
            except Exception as exc:  # pragma: no cover
                app_logger.exception("Failed to load encoder artifact: %s", exc)

    def compute_amount_threshold(self) -> None:
        fallback = 1.0
        try:
            raw_data_path = Path.cwd() / "data" / "raw" / "AIML Dataset.csv"
            if raw_data_path.exists():
                df = pd.read_csv(raw_data_path, usecols=["amount"])
                self.amount_threshold = float(df["amount"].quantile(0.95))
                app_logger.info("Computed amount threshold from dataset: %s", self.amount_threshold)
            else:
                self.amount_threshold = fallback
                app_logger.warning("Raw dataset not found for amount threshold; using fallback %s", fallback)
        except Exception as exc:  # pragma: no cover
            self.amount_threshold = fallback
            app_logger.exception("Failed to compute amount threshold: %s", exc)

    def _looks_like_legacy_payload(self, input_data: dict[str, Any]) -> bool:
        legacy_keys = {"age", "income", "transaction_amount", "risk_score", "department", "user_role"}
        return bool(legacy_keys.intersection(input_data.keys()))

    def _preprocess_legacy_payload(self, input_data: dict[str, Any]) -> np.ndarray:
        age = float(input_data.get("age") or 0.0)
        income = float(input_data.get("income") or 0.0)
        transaction_amount = float(input_data.get("transaction_amount") or input_data.get("amount") or 0.0)
        risk_score = float(input_data.get("risk_score") or 0.0)
        department = str(input_data.get("department") or "finance")
        user_role = str(input_data.get("user_role") or "user")

        numeric_features = np.array([[age, income, transaction_amount, risk_score]], dtype=float)
        if self.scaler is not None:
            numeric_features = self.scaler.transform(numeric_features)

        categorical_features = np.array([[department, user_role]], dtype=object)
        if self.encoder is not None:
            encoded = self.encoder.transform(categorical_features)
            if hasattr(encoded, "toarray"):
                encoded = encoded.toarray()
            encoded = np.asarray(encoded).reshape(-1)
            return np.hstack((np.asarray(numeric_features).reshape(-1), encoded)).astype(float)

        return np.hstack((np.asarray(numeric_features).reshape(-1), np.array([0.0, 0.0], dtype=float))).astype(float)

    def preprocess_batch(self, inputs: list[dict[str, Any]]) -> np.ndarray:
        if not inputs:
            raise RuntimeError("No inputs provided")

        if self._looks_like_legacy_payload(inputs[0]):
            return np.asarray([self._preprocess_legacy_payload(item) for item in inputs], dtype=float)

        if self.feature_config is None or not self.model_feature_order:
            raise RuntimeError("Preprocessing service is not configured")

        engineered = [self.engineer_transaction_features(item) for item in inputs]
        return np.asarray(engineered, dtype=float)

    def preprocess_single(self, input_data: dict[str, Any]) -> np.ndarray:
        return self.preprocess_batch([input_data])

    def engineer_transaction_features(self, input_data: dict[str, Any]) -> list[float]:
        type_mapping = {
            "CASH_IN": 0,
            "CASH_OUT": 1,
            "DEBIT": 2,
            "PAYMENT": 3,
            "TRANSFER": 4,
        }

        raw_type = str(input_data.get("type") or "TRANSFER").upper()
        type_code = type_mapping.get(raw_type, 4)

        amount = float(input_data.get("amount") or 0.0)
        oldbalanceOrg = float(input_data.get("oldbalanceOrg") or 0.0)
        newbalanceOrig = float(input_data.get("newbalanceOrig") or 0.0)
        oldbalanceDest = float(input_data.get("oldbalanceDest") or 0.0)
        newbalanceDest = float(input_data.get("newbalanceDest") or 0.0)
        step = int(input_data.get("step") or 0)

        origin_delta = oldbalanceOrg - newbalanceOrig
        dest_delta = newbalanceDest - oldbalanceDest
        is_transfer = 1.0 if type_code == 4 else 0.0
        is_cashout = 1.0 if type_code == 1 else 0.0
        amount_to_balance = amount / (oldbalanceOrg if oldbalanceOrg != 0 else 1e-6)
        dest_to_origin_ratio = newbalanceDest / (oldbalanceDest if oldbalanceDest != 0 else 1e-6)
        amount_log = np.log1p(amount)
        oldbalanceOrg_log = np.log1p(oldbalanceOrg)
        newbalanceOrig_log = np.log1p(newbalanceOrig)
        balance_error_orig = oldbalanceOrg - amount - newbalanceOrig
        balance_error_dest = oldbalanceDest + amount - newbalanceDest
        amount_ratio_orig = amount / (oldbalanceOrg + 1)
        amount_ratio_dest = amount / (oldbalanceDest + 1)
        orig_zeroed_out = 1.0 if (oldbalanceOrg > 0 and newbalanceOrig == 0) else 0.0
        dest_unchanged = 1.0 if oldbalanceDest == newbalanceDest else 0.0
        full_drain = 1.0 if (origin_delta > 0 and newbalanceOrig == 0) else 0.0
        transfer_x_drain = is_transfer * full_drain
        cashout_x_drain = is_cashout * full_drain
        high_amount_flag = 1.0 if amount > self.amount_threshold else 0.0

        feature_values = {
            "step": float(step),
            "type": float(type_code),
            "amount": amount,
            "oldbalanceOrg": oldbalanceOrg,
            "newbalanceOrig": newbalanceOrig,
            "oldbalanceDest": oldbalanceDest,
            "newbalanceDest": newbalanceDest,
            "origin_delta": origin_delta,
            "dest_delta": dest_delta,
            "is_transfer": is_transfer,
            "is_cashout": is_cashout,
            "amount_to_balance": amount_to_balance,
            "dest_to_origin_ratio": dest_to_origin_ratio,
            "amount_log": amount_log,
            "oldbalanceOrg_log": oldbalanceOrg_log,
            "newbalanceOrig_log": newbalanceOrig_log,
            "balance_error_orig": balance_error_orig,
            "balance_error_dest": balance_error_dest,
            "amount_ratio_orig": amount_ratio_orig,
            "amount_ratio_dest": amount_ratio_dest,
            "orig_zeroed_out": orig_zeroed_out,
            "dest_unchanged": dest_unchanged,
            "full_drain": full_drain,
            "transfer_x_drain": transfer_x_drain,
            "cashout_x_drain": cashout_x_drain,
            "high_amount_flag": high_amount_flag,
        }

        ordered = []
        for feature in self.model_feature_order:
            if feature in feature_values:
                ordered.append(feature_values[feature])
            else:
                ordered.append(0.0)
        return ordered


preprocessing_service = PreprocessingService()
feature_config = preprocessing_service.feature_config
num_features = preprocessing_service.num_features
cat_features = preprocessing_service.cat_features
scaler = preprocessing_service.scaler
encoder = preprocessing_service.encoder
configured = preprocessing_service.configured

