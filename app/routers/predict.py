import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, HTTPException, status
from app.schemas.prediction import (
    PredictionInput, 
    PredictionResponse, 
    BatchPredictionInput, 
    BatchPredictionResponse
)
from app.dependencies import verify_jwt_or_api_key
from app.services.preprocessing_service import preprocessing_service
from app.services.model_service import model_service

router = APIRouter()

@router.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_single(
    request: Request,
    input_payload: PredictionInput,
    current_user: dict = Depends(verify_jwt_or_api_key)
) -> PredictionResponse:
    """
    Predict risk rating (0 or 1) for a single input record.
    Supports:
    - **JWT Authentication** (requires header: `Authorization: Bearer <token>` with Analyst or Admin role).
    - **API Key Authentication** (requires header: `X-API-Key: <key>` for service-to-service).
    """
    start_time = time.perf_counter()
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Check if model is configured/loaded
    if model_service.model is None or preprocessing_service.feature_config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML Model is not configured. Please place the official model artifacts in the models/ directory."
        )
    
    # 1. Transform request schema to dict
    features_dict = input_payload.model_dump()
    
    # 2. Preprocess input
    processed_features = preprocessing_service.preprocess_single(features_dict)
    
    # 3. Model Inference (runs in thread pool as this is a synchronous endpoint)
    predictions, probabilities = model_service.predict(processed_features)
    
    # Output values
    pred_class = int(predictions[0])
    # Return probability of class 1 (high risk)
    pred_prob = float(probabilities[0][-1])
    
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    return PredictionResponse(
        prediction=pred_class,
        probability=pred_prob,
        model_version=model_service.model_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
        processing_time_ms=round(latency_ms, 2)
    )

@router.post("/batch-predict", response_model=BatchPredictionResponse, tags=["Inference"])
def predict_batch(
    request: Request,
    batch_payload: BatchPredictionInput,
    current_user: dict = Depends(verify_jwt_or_api_key)
) -> BatchPredictionResponse:
    """
    Predict risk rating for multiple input records.
    Supports:
    - **JWT Authentication** (requires header: `Authorization: Bearer <token>` with Analyst or Admin role).
    - **API Key Authentication** (requires header: `X-API-Key: <key>` for service-to-service).
    """
    start_time = time.perf_counter()
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Check if model is configured/loaded
    if model_service.model is None or preprocessing_service.feature_config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML Model is not configured. Please place the official model artifacts in the models/ directory."
        )
    
    # 1. Preprocess batch
    inputs_list = [item.model_dump() for item in batch_payload.inputs]
    processed_features = preprocessing_service.preprocess_batch(inputs_list)
    
    # 2. Batch Inference (runs in thread pool as this is a synchronous endpoint)
    predictions, probabilities = model_service.predict(processed_features)
    
    # 3. Format individual responses
    individual_responses = []
    timestamp_str = datetime.now(timezone.utc).isoformat()
    
    for i in range(len(inputs_list)):
        individual_responses.append(
            PredictionResponse(
                prediction=int(predictions[i]),
                probability=float(probabilities[i][-1]),
                model_version=model_service.model_version,
                timestamp=timestamp_str,
                request_id=request_id,
                processing_time_ms=0.0 # Individual latency not isolated in batch
            )
        )
        
    total_latency_ms = (time.perf_counter() - start_time) * 1000
    
    return BatchPredictionResponse(
        predictions=individual_responses,
        model_version=model_service.model_version,
        request_id=request_id,
        processing_time_ms=round(total_latency_ms, 2)
    )
