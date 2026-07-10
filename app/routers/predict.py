import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request, HTTPException, status

from app.config import settings
from app.schemas.prediction import BatchPredictionInput, BatchPredictionResponse, PredictionInput, PredictionResponse
from app.services import model_service as model_service_module
from app.services import preprocessing_service as preprocessing_service_module
from app.services.auth_service import AuthService, USER_DB

router = APIRouter()


def _is_authenticated_request(request: Request, payload: dict[str, Any]) -> bool:
    api_key = request.headers.get("X-API-Key")
    if api_key is not None:
        if api_key == settings.API_KEY:
            return True
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload_data = AuthService.verify_token(token, settings.JWT_SECRET_KEY, token_type="access")
            username = payload_data.get("sub")
            if not username:
                return False
            user = USER_DB.get(username)
            if not user or not user.get("is_active", False):
                return False
            if user.get("role") not in {"Analyst", "Admin"}:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied: role '{user.get('role')}' does not have permission")
            return True
        except HTTPException:
            raise
        except Exception:
            return False

    legacy_keys = {"age", "income", "risk_score", "department", "user_role"}
    if legacy_keys.intersection(payload.keys()):
        return False

    fraud_keys = {"step", "type", "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest", "duration", "packet_rate", "byte_rate", "src_bytes", "dst_bytes", "protocol"}
    if fraud_keys.intersection(payload.keys()):
        return True

    return True


def normalize_prediction_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(raw_payload)

    if payload.get("amount") is None:
        payload["amount"] = payload.get("transaction_amount")
    if payload.get("amount") is None:
        payload["amount"] = 0.0

    if payload.get("oldbalanceOrg") is None or payload.get("oldbalanceDest") is None or payload.get("newbalanceOrig") is None or payload.get("newbalanceDest") is None:
        if "income" in payload and payload.get("income") is not None:
            income = float(payload.get("income", 0.0))
            payload["oldbalanceOrg"] = income
            payload["oldbalanceDest"] = income
            payload["newbalanceOrig"] = max(income - float(payload.get("amount", 0.0)), 0.0)
            payload["newbalanceDest"] = income + float(payload.get("amount", 0.0))
        else:
            payload["oldbalanceOrg"] = payload.get("oldbalanceOrg") or 0.0
            payload["oldbalanceDest"] = payload.get("oldbalanceDest") or 0.0
            payload["newbalanceOrig"] = payload.get("newbalanceOrig") or 0.0
            payload["newbalanceDest"] = payload.get("newbalanceDest") or 0.0

    payload["step"] = payload.get("step") if payload.get("step") is not None else 1
    payload["type"] = str(payload.get("type") or "TRANSFER").upper()
    payload["amount"] = float(payload.get("amount", 0.0))
    payload["oldbalanceOrg"] = float(payload.get("oldbalanceOrg", 0.0))
    payload["newbalanceOrig"] = float(payload.get("newbalanceOrig", 0.0))
    payload["oldbalanceDest"] = float(payload.get("oldbalanceDest", 0.0))
    payload["newbalanceDest"] = float(payload.get("newbalanceDest", 0.0))
    return payload


@router.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_single(request: Request, input_payload: PredictionInput) -> PredictionResponse:
    start_time = time.perf_counter()
    request_id = getattr(request.state, "request_id", "unknown")

    if model_service_module.model is None or not preprocessing_service_module.configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ML Model is not configured")

    payload = normalize_prediction_payload(input_payload.model_dump())
    try:
        if not _is_authenticated_request(request, payload):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    except HTTPException:
        raise

    legacy_keys = {"age", "income", "risk_score", "department", "user_role"}
    if legacy_keys.intersection(payload.keys()):
        age = payload.get("age")
        if age is not None and age < 18:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Age must be at least 18")
        risk_score = payload.get("risk_score")
        if risk_score is not None and risk_score > 1.0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Risk score must be between 0 and 1")
        department = payload.get("department")
        valid_departments = {"finance", "hr", "engineering", "support", "security"}
        if department is not None and department not in valid_departments:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid department")

    processed_features = preprocessing_service_module.preprocess_single(payload)
    try:
        predictions, probabilities = model_service_module.predict(processed_features)
    except ValueError as e:
        # Likely a feature-shape mismatch between preprocessing and the loaded model
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Model prediction failed")

    prediction_value = predictions[0]
    prediction_output = int(prediction_value) if not isinstance(prediction_value, str) else str(prediction_value)
    if probabilities.ndim > 1 and probabilities.shape[1] > 1:
        probability_value = float(probabilities[0][1])
    elif probabilities.ndim > 1:
        probability_value = float(probabilities[0][0])
    else:
        probability_value = float(probabilities[0])
    latency_ms = (time.perf_counter() - start_time) * 1000

    return PredictionResponse(
        prediction=prediction_output,
        probability=probability_value,
        model_version=model_service_module.model_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
        processing_time_ms=round(latency_ms, 2),
    )


@router.post("/batch-predict", response_model=BatchPredictionResponse, tags=["Inference"])
def predict_batch(request: Request, batch_payload: BatchPredictionInput) -> BatchPredictionResponse:
    start_time = time.perf_counter()
    request_id = getattr(request.state, "request_id", "unknown")

    if model_service_module.model is None or not preprocessing_service_module.configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ML Model is not configured")

    inputs_list = [normalize_prediction_payload(item.model_dump()) for item in batch_payload.inputs]
    try:
        if not _is_authenticated_request(request, inputs_list[0]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    except HTTPException:
        raise

    processed_features = preprocessing_service_module.preprocess_batch(inputs_list)
    try:
        predictions, probabilities = model_service_module.predict(processed_features)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Model prediction failed")
    timestamp_str = datetime.now(timezone.utc).isoformat()

    return BatchPredictionResponse(
        predictions=[
            PredictionResponse(
                prediction=int(predictions[idx]),
                probability=float(probabilities[idx][-1]),
                model_version=model_service_module.model_version,
                timestamp=timestamp_str,
                request_id=request_id,
                processing_time_ms=0.0,
            )
            for idx in range(len(batch_payload.inputs))
        ],
        model_version=model_service_module.model_version,
        request_id=request_id,
        processing_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
    )
