import os
import sys
from pathlib import Path

import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.model_service import ModelService


class DummyModel:
    pass


def test_model_service_prefers_xgboost_when_present(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    joblib.dump(DummyModel(), models_dir / "catboost_fraud_detector.joblib")
    joblib.dump(DummyModel(), models_dir / "xgboost_fraud_detector.joblib")

    monkeypatch.setenv("MODEL_DIR", str(models_dir))
    monkeypatch.delenv("MODEL_FILE", raising=False)

    service = ModelService()

    assert service.model_version == "xgboost_fraud_detector"
