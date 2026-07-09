import os
import sys
import pytest

# Add the project directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import USER_DB

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_health_endpoint():
    response = client.get("/health")
    if not os.path.exists("models/best_model.pkl"):
        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "HTTP Error"
        assert data["message"]["status"] == "unhealthy"
        assert data["message"]["details"]["model_loaded"] is False
    else:
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["details"]["model_loaded"] is True

def test_version_endpoint():
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "api_version" in data
    assert "model_version" in data

def test_login_successful():
    response = client.post("/login", json={
        "username": "analyst",
        "password": "AnalystPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "Analyst"

def test_login_failed_wrong_password():
    response = client.post("/login", json={
        "username": "analyst",
        "password": "WrongPassword123!"
    })
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["message"]

def test_login_invalid_username():
    response = client.post("/login", json={
        "username": "user; drop table users;--",
        "password": "UserPass123!"
    })
    # Username format validation fails regex
    assert response.status_code == 422
    assert "Validation Error" in response.json()["error"]

def test_refresh_token_successful():
    # Login to get refresh token
    login_resp = client.post("/login", json={
        "username": "analyst",
        "password": "AnalystPass123!"
    })
    refresh_token = login_resp.json()["refresh_token"]
    
    # Use refresh token
    response = client.post("/refresh-token", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

def test_refresh_token_invalid():
    response = client.post("/refresh-token", json={
        "refresh_token": "invalid_refresh_token_value_here"
    })
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["message"]

def test_prediction_without_auth():
    response = client.post("/predict", json={
        "age": 35,
        "income": 75000.0,
        "transaction_amount": 120.50,
        "risk_score": 0.23,
        "department": "finance",
        "user_role": "user"
    })
    assert response.status_code == 401

def test_prediction_forbidden_role():
    # Login as normal 'user'
    login_resp = client.post("/login", json={
        "username": "user",
        "password": "UserPass123!"
    })
    access_token = login_resp.json()["access_token"]
    
    # Try predicting
    response = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "age": 35,
            "income": 75000.0,
            "transaction_amount": 120.50,
            "risk_score": 0.23,
            "department": "finance",
            "user_role": "user"
        }
    )
    assert response.status_code == 403
    assert "role 'User' does not have permission" in response.json()["message"]

def test_prediction_authorized_role():
    # Login as 'analyst'
    login_resp = client.post("/login", json={
        "username": "analyst",
        "password": "AnalystPass123!"
    })
    access_token = login_resp.json()["access_token"]
    
    # Predict
    response = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "age": 35,
            "income": 75000.0,
            "transaction_amount": 120.50,
            "risk_score": 0.23,
            "department": "finance",
            "user_role": "user"
        }
    )
    if not os.path.exists("models/best_model.pkl"):
        assert response.status_code == 503
        assert "ML Model is not configured" in response.json()["message"]
    else:
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert isinstance(data["prediction"], int)
        assert "probability" in data
        assert data["model_version"] == "1.0.0"
        assert "request_id" in data
        assert data["processing_time_ms"] > 0.0

def test_prediction_validation_rules():
    # Login as 'analyst'
    login_resp = client.post("/login", json={
        "username": "analyst",
        "password": "AnalystPass123!"
    })
    access_token = login_resp.json()["access_token"]
    
    # 1. Invalid age (too young)
    response1 = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "age": 12,
            "income": 75000.0,
            "transaction_amount": 120.50,
            "risk_score": 0.23,
            "department": "finance",
            "user_role": "user"
        }
    )
    assert response1.status_code == 422
    
    # 2. Risk score out of range (> 1.0)
    response2 = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "age": 35,
            "income": 75000.0,
            "transaction_amount": 120.50,
            "risk_score": 1.5,
            "department": "finance",
            "user_role": "user"
        }
    )
    assert response2.status_code == 422

    # 3. Invalid categorical choice
    response3 = client.post(
        "/predict",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "age": 35,
            "income": 75000.0,
            "transaction_amount": 120.50,
            "risk_score": 0.5,
            "department": "unauthorized-dept",
            "user_role": "user"
        }
    )
    assert response3.status_code == 422

def test_batch_prediction_authorized():
    # Login as 'analyst'
    login_resp = client.post("/login", json={
        "username": "analyst",
        "password": "AnalystPass123!"
    })
    access_token = login_resp.json()["access_token"]
    
    # Batch predict
    response = client.post(
        "/batch-predict",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "inputs": [
                {
                    "age": 35,
                    "income": 75000.0,
                    "transaction_amount": 120.50,
                    "risk_score": 0.23,
                    "department": "finance",
                    "user_role": "user"
                },
                {
                    "age": 42,
                    "income": 120000.0,
                    "transaction_amount": 1500.00,
                    "risk_score": 0.81,
                    "department": "healthcare",
                    "user_role": "admin"
                }
            ]
        }
    )
    if not os.path.exists("models/best_model.pkl"):
        assert response.status_code == 503
    else:
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert len(data["predictions"]) == 2
        assert "model_version" in data
        assert "request_id" in data

def test_prediction_with_api_key_authorized():
    response = client.post(
        "/predict",
        headers={"X-API-Key": "local-dev-api-key-replace-in-production"},
        json={
            "age": 35,
            "income": 75000.0,
            "transaction_amount": 120.50,
            "risk_score": 0.23,
            "department": "finance",
            "user_role": "user"
        }
    )
    if not os.path.exists("models/best_model.pkl"):
        assert response.status_code == 503
        data = response.json()
        assert "ML Model is not configured" in data["message"]
    else:
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "probability" in data
        assert data["model_version"] == "1.0.0"

def test_prediction_with_api_key_invalid():
    response = client.post(
        "/predict",
        headers={"X-API-Key": "invalid-api-key-value"},
        json={
            "age": 35,
            "income": 75000.0,
            "transaction_amount": 120.50,
            "risk_score": 0.23,
            "department": "finance",
            "user_role": "user"
        }
    )
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["message"]

def test_batch_prediction_with_api_key_authorized():
    response = client.post(
        "/batch-predict",
        headers={"X-API-Key": "local-dev-api-key-replace-in-production"},
        json={
            "inputs": [
                {
                    "age": 35,
                    "income": 75000.0,
                    "transaction_amount": 120.50,
                    "risk_score": 0.23,
                    "department": "finance",
                    "user_role": "user"
                }
            ]
        }
    )
    if not os.path.exists("models/best_model.pkl"):
        assert response.status_code == 503
    else:
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert len(data["predictions"]) == 1

@pytest.mark.skipif(not os.path.exists("models/best_model.pkl"), reason="Official model not integrated yet")
def test_compare_model_vs_api():
    # Compare raw model prediction vs API endpoint response
    import joblib
    import numpy as np

    model = joblib.load("models/best_model.pkl")
    scaler = joblib.load("models/scaler.pkl")
    encoder = joblib.load("models/encoder.pkl")

    sample_flow = {
        "age": 35,
        "income": 75000.0,
        "transaction_amount": 120.50,
        "risk_score": 0.23,
        "department": "finance",
        "user_role": "user"
    }

    num_array = np.array([[
        sample_flow["age"],
        sample_flow["income"],
        sample_flow["transaction_amount"],
        sample_flow["risk_score"]
    ]])
    scaled_num = scaler.transform(num_array)

    cat_array = np.array([[
        sample_flow["department"],
        sample_flow["user_role"]
    ]])
    encoded_cat = encoder.transform(cat_array)

    X_test = np.hstack((scaled_num, encoded_cat))

    direct_pred = int(model.predict(X_test)[0])
    direct_prob = float(model.predict_proba(X_test)[0][1])

    response = client.post(
        "/predict",
        headers={"X-API-Key": "local-dev-api-key-replace-in-production"},
        json=sample_flow
    )
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == direct_pred
    assert abs(data["probability"] - direct_prob) < 1e-6

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))
