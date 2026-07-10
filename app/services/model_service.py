import json
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.services.logging_service import app_logger


class ModelService:
    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parents[2]
        models_dir = Path(os.getenv("MODEL_DIR", base_dir / "models"))
        if not models_dir.exists():
            fallback_dir = Path.cwd() / "models"
            if fallback_dir.exists():
                models_dir = fallback_dir

        self.model: Any = None
        self.model_version = "unknown"

        # Allow explicit selection via MODEL_FILE env var
        env_model_file = os.getenv("MODEL_FILE")
        candidates = []
        if env_model_file:
            candidates.append(models_dir / env_model_file)

        # Prefer the official best_model artifact when present, but fall back to the XGBoost fraud model otherwise.
        candidates.extend([
            models_dir / "best_model.pkl",
            models_dir / "best_model.joblib",
            models_dir / "xgboost_fraud_detector.joblib",
            models_dir / "catboost_fraud_detector.joblib",
            models_dir / "lightgbm_fraud_detector.joblib",
        ])

        # Add any other supported model file from the models dir
        for ext in ("*.joblib", "*.pkl", "*.model"):
            for p in sorted(models_dir.glob(ext)):
                if p not in candidates:
                    candidates.append(p)

        model_path = None
        for cand in candidates:
            if cand.exists():
                model_path = cand
                break

        if model_path is None:
            app_logger.warning("No trained model found in %s; predictions will return 503 until a model is placed there", models_dir)
            globals()["model"] = self.model
            globals()["model_version"] = self.model_version
            return

        try:
            # joblib can load many sklearn-compatible models and serialized objects
            self.model = joblib.load(model_path)
            self.model_version = os.getenv("MODEL_VERSION") or getattr(self.model, "version", None)
            if not self.model_version:
                if model_path.stem in {"xgboost_fraud_detector", "catboost_fraud_detector", "lightgbm_fraud_detector"}:
                    self.model_version = model_path.stem
                else:
                    self.model_version = "1.0.0"
            try:
                metadata_path = models_dir / "ensemble_metadata.json"
                if metadata_path.exists():
                    with metadata_path.open("r", encoding="utf-8") as handle:
                        metadata = json.load(handle)
                    if metadata.get("model_version"):
                        self.model_version = metadata["model_version"]
            except Exception:
                pass
            app_logger.info("Loaded ML model from %s (version=%s)", model_path, self.model_version)
        except Exception as exc:  # pragma: no cover
            app_logger.exception("Failed to load ML model from %s: %s", model_path, exc)

        globals()["model"] = self.model
        globals()["model_version"] = self.model_version

    def predict(self, features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        predictions = np.asarray(self.model.predict(features))
        if hasattr(self.model, "predict_proba"):
            probabilities = np.asarray(self.model.predict_proba(features))
            if probabilities.ndim == 1:
                probabilities = probabilities.reshape(-1, 1)
            if probabilities.shape[1] == 1:
                positive = probabilities[:, 0]
                probabilities = np.column_stack((1 - positive, positive))
            else:
                positive = probabilities[:, -1]
                probabilities = np.column_stack((1 - positive, positive))
        else:
            probabilities = np.column_stack((1 - predictions.astype(float), predictions.astype(float)))

        return predictions, probabilities


model_service = ModelService()
model = model_service.model
model_version = model_service.model_version

