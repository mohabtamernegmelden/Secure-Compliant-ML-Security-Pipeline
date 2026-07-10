import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services import model_service, preprocessing_service


client = TestClient(app)


class DummyModel:
    def predict(self, X):
        return np.array([1 if float(X[0, 0]) > 0.5 else 0 for _ in range(len(X))])

    def predict_proba(self, X):
        return np.array([[0.2, 0.8] for _ in range(len(X))])


def test_health_endpoint_reports_model_status():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert "model_loaded" in payload


def test_predict_endpoint_returns_prediction_when_model_loaded(monkeypatch):
    monkeypatch.setattr(model_service, "model", DummyModel())
    monkeypatch.setattr(model_service, "model_version", "test-model")
    monkeypatch.setattr(preprocessing_service, "feature_config", {
        "numerical_features": ["duration", "packet_rate", "byte_rate", "src_bytes", "dst_bytes"],
        "categorical_features": ["protocol"],
        "categories": {"protocol": ["TCP", "UDP", "ICMP"]},
    })
    monkeypatch.setattr(preprocessing_service, "num_features", ["duration", "packet_rate", "byte_rate", "src_bytes", "dst_bytes"])
    monkeypatch.setattr(preprocessing_service, "cat_features", ["protocol"])
    monkeypatch.setattr(preprocessing_service, "scaler", None)
    monkeypatch.setattr(preprocessing_service, "encoder", None)

    response = client.post(
        "/predict",
        json={
            "duration": 0.75,
            "packet_rate": 120.0,
            "byte_rate": 2048.0,
            "src_bytes": 400,
            "dst_bytes": 800,
            "protocol": "TCP",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["prediction"] in {0, 1, "BENIGN", "ATTACK"}
    assert 0.0 <= payload["probability"] <= 1.0
    assert payload["model_version"] == "test-model"


def test_predict_endpoint_returns_503_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(model_service, "model", None)
    monkeypatch.setattr(model_service, "model_version", "unknown")

    response = client.post(
        "/predict",
        json={
            "duration": 0.1,
            "packet_rate": 50.0,
            "byte_rate": 500.0,
            "src_bytes": 100,
            "dst_bytes": 120,
            "protocol": "UDP",
        },
    )

    assert response.status_code == 503


def test_compare_model_vs_api(monkeypatch):
    monkeypatch.setattr(model_service, "model", DummyModel())
    monkeypatch.setattr(model_service, "model_version", "test-model")
    monkeypatch.setattr(preprocessing_service, "feature_config", {
        "numerical_features": ["duration", "packet_rate", "byte_rate", "src_bytes", "dst_bytes"],
        "categorical_features": ["protocol"],
        "categories": {"protocol": ["TCP", "UDP", "ICMP"]},
    })
    monkeypatch.setattr(preprocessing_service, "num_features", ["duration", "packet_rate", "byte_rate", "src_bytes", "dst_bytes"])
    monkeypatch.setattr(preprocessing_service, "cat_features", ["protocol"])
    monkeypatch.setattr(preprocessing_service, "scaler", None)
    monkeypatch.setattr(preprocessing_service, "encoder", None)

    payload = {
        "duration": 0.9,
        "packet_rate": 180.0,
        "byte_rate": 4096.0,
        "src_bytes": 500,
        "dst_bytes": 900,
        "protocol": "ICMP",
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["prediction"] in {0, 1, "BENIGN", "ATTACK"}
