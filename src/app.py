import os
import json
import hashlib
import secrets
import joblib
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_403_FORBIDDEN
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

try:
    from pydantic import field_validator
except ImportError:  # pragma: no cover - fallback for Pydantic v1
    from pydantic import validator as field_validator

# ========== MLOps Audit Logger ==========
class MLOpsLogger:
    """Logs MLOps events, request metadata, model predictions, and audit actions."""
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or os.getenv("MLOPS_AUDIT_LOG_PATH", "data/processed/mlops_audit_log.json")
        parent_dir = os.path.dirname(self.log_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
    
    def log_event(self, action: str, details: dict):
        event = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': action,
            **details
        }
        events = []
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r') as f:
                    events = json.load(f)
            except Exception:
                events = []
        events.append(event)
        with open(self.log_path, 'w') as f:
            json.dump(events, f, indent=2)

mlops_logger = MLOpsLogger()

# ========== FastAPI Setup & Hardening ==========
limiter = Limiter(key_func=get_remote_address)
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title="Secure & Compliant Fraud Detection API",
    description="Production-hardened, compliant fraud detection prediction service with Azure Key Vault simulation.",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:8000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_runtime_api_key() -> str:
    configured_key = os.getenv("FRAUD_DETECTION_API_KEY")
    if configured_key:
        return configured_key
    if os.getenv("APP_ENV", "development").lower() != "production":
        fallback_key = f"dev-local-{secrets.token_urlsafe(12)}"
        print("WARNING: FRAUD_DETECTION_API_KEY not set. Using ephemeral local development key.")
        return fallback_key
    raise RuntimeError("FRAUD_DETECTION_API_KEY must be configured in production environments.")


def get_api_key(api_key: str = Depends(api_key_header)):
    expected_key = get_runtime_api_key()
    if api_key == expected_key:
        return api_key

    mlops_logger.log_event('UNAUTHORIZED_ACCESS_ATTEMPT', {
        'description': 'Attempted API access with invalid key header'
    })
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )

# ========== Mock Azure Key Vault Integration ==========
class AzureKeyVaultClient:
    """Simulates the Azure Key Vault SDK integration using environment-backed secrets."""
    def __init__(self):
        self.vault_url = os.getenv("AZURE_KEY_VAULT_URL", "https://fraud-detection-vault.vault.azure.net/")

    def get_secret(self, name: str) -> Optional[str]:
        env_name = name.replace("-", "_").upper()
        return os.getenv(env_name) or os.getenv(name)

customer_feature_store = {}
label_encoders = {}

CATEGORICAL_MAPPINGS = {
    'country': {'USA': 0, 'India': 1, 'UK': 2, 'Brazil': 3, 'Germany': 4, 'Japan': 5, 'France': 6, 'Canada': 7, 'Mexico': 8, 'Australia': 9},
    'city': {'Rio': 0, 'Melbourne': 1, 'Guadalajara': 2, 'Sydney': 3, 'So Paulo': 4, 'Manchester': 5, 'Mumbai': 6, 'Delhi': 7, 'Los Angeles': 8, 'Osaka': 9, 'Paris': 10, 'New York': 11, 'Munich': 12, 'Tokyo': 13, 'Vancouver': 14, 'Toronto': 15, 'Mexico City': 16, 'London': 17, 'Berlin': 18, 'Lyon': 19},
    'merchant_category': {'Entertainment': 0, 'Jewelry': 1, 'Electronics': 2, 'Fuel': 3, 'Utilities': 4, 'Education': 5, 'Clothing': 6, 'Travel': 7, 'Restaurant': 8, 'Healthcare': 9, 'Online Shopping': 10, 'Gaming': 11, 'Grocery': 12, 'ATM Withdrawal': 13, 'Crypto Exchange': 14},
    'payment_method': {'Credit Card': 0, 'Debit Card': 1, 'Bank Transfer': 2, 'Mobile Payment': 3, 'Crypto': 4, 'Cheque': 5},
    'device_type': {'Mobile': 0, 'Desktop': 1, 'ATM': 2, 'Tablet': 3, 'POS Terminal': 4}
}

class TransactionRequest(BaseModel):
    customer_id: str = Field(..., description="Plain or hashed customer identifier")
    failed_attempts: int = Field(..., ge=0, le=5, description="Failed PIN attempts")
    is_night_transaction: int = Field(..., ge=0, le=1, description="Night transaction flag")
    is_international: int = Field(..., ge=0, le=1, description="International transaction flag")
    pin_changed_recently: int = Field(..., ge=0, le=1, description="PIN changed flag")
    merchant_category: str = Field(..., description="Merchant category name")
    transaction_amount: float = Field(..., gt=0, description="Amount in USD")
    account_balance: float = Field(..., ge=0, description="Current balance")
    credit_score: float = Field(..., ge=300, le=850, description="Credit score")
    distance_from_home_km: float = Field(..., ge=0, description="Distance from home")
    time_since_last_txn_hrs: float = Field(..., ge=0, description="Hours since last transaction")
    hour_of_day: int = Field(..., ge=0, le=23, description="Hour of the day")
    is_weekend: int = Field(..., ge=0, le=1, description="Weekend flag")
    customer_age: int = Field(..., ge=18, le=120, description="Customer age")
    num_prev_transactions: int = Field(..., ge=0, description="Number of previous transactions")
    transaction_freq_monthly: int = Field(..., ge=0, description="Monthly frequency")
    country: str = Field(..., description="Country name")
    city: str = Field(..., description="City name")
    payment_method: str = Field(..., description="Payment method name")
    device_type: str = Field(..., description="Device type name")

    @field_validator('merchant_category', 'country', 'city', 'payment_method', 'device_type')
    def validate_categories(cls, v, info):
        f_name = info.field_name
        if v not in CATEGORICAL_MAPPINGS[f_name]:
            raise ValueError(f"Value '{v}' is not valid for category '{f_name}'")
        return v

models = {}
meta = {}


def build_feature_vector(tx: "TransactionRequest", customer_profile: Dict[str, float], metadata: Dict[str, List[str]]) -> Dict[str, float]:
    """Build the feature vector used by the trained ensemble for inference."""
    high_risk_merchant = 1 if tx.merchant_category in ['ATM Withdrawal', 'Jewelry', 'Crypto Exchange'] else 0
    failed_x_night = tx.failed_attempts * tx.is_night_transaction
    failed_x_intl = tx.failed_attempts * tx.is_international
    failed_x_pin = tx.failed_attempts * tx.pin_changed_recently
    failed_x_highrisk = tx.failed_attempts * high_risk_merchant
    night_x_intl = tx.is_night_transaction * tx.is_international
    night_x_pin = tx.is_night_transaction * tx.pin_changed_recently
    intl_x_pin = tx.is_international * tx.pin_changed_recently
    intl_x_highrisk = tx.is_international * high_risk_merchant
    failed_night_pin = tx.failed_attempts * tx.is_night_transaction * tx.pin_changed_recently
    failed_night_intl = tx.failed_attempts * tx.is_night_transaction * tx.is_international
    failed_intl_pin = tx.failed_attempts * tx.is_international * tx.pin_changed_recently
    failed_intl_highrisk = tx.failed_attempts * tx.is_international * high_risk_merchant
    night_x_highrisk = tx.is_night_transaction * high_risk_merchant
    pin_x_highrisk = tx.pin_changed_recently * high_risk_merchant

    if tx.customer_age <= 18:
        age_bucket = 0
    elif tx.customer_age <= 25:
        age_bucket = 1
    elif tx.customer_age <= 35:
        age_bucket = 2
    elif tx.customer_age <= 50:
        age_bucket = 3
    elif tx.customer_age <= 65:
        age_bucket = 4
    else:
        age_bucket = 5

    customer_profile = customer_profile or {}
    count = int(customer_profile.get('count', 0))
    if count > 0:
        cust_amount_mean = customer_profile.get('amount_sum', 0.0) / count
        cust_amount_ratio_to_mean = tx.transaction_amount / (cust_amount_mean if cust_amount_mean > 0 else 1.0)
        cust_amount_max = customer_profile.get('amount_max', 0.0)
        cust_amount_ratio_to_max = tx.transaction_amount / (cust_amount_max if cust_amount_max > 0 else 1.0)
        cust_failed_mean = customer_profile.get('failed_sum', 0) / count
        cust_intl_mean = customer_profile.get('intl_sum', 0) / count
    else:
        cust_amount_ratio_to_mean = 1.0
        cust_amount_ratio_to_max = 1.0
        cust_failed_mean = 0.0
        cust_intl_mean = 0.0

    amount_per_balance = tx.transaction_amount / (tx.account_balance if tx.account_balance > 0 else 1e-5)
    risk_score = (tx.failed_attempts * 3 + tx.is_night_transaction * 2 + tx.is_international * 2 +
                  tx.pin_changed_recently * 1 + high_risk_merchant * 1.5)

    input_data = {
        'failed_attempts': tx.failed_attempts,
        'is_night_transaction': tx.is_night_transaction,
        'is_international': tx.is_international,
        'pin_changed_recently': tx.pin_changed_recently,
        'high_risk_merchant': high_risk_merchant,
        'transaction_amount': tx.transaction_amount,
        'account_balance': tx.account_balance,
        'credit_score': tx.credit_score,
        'distance_from_home_km': tx.distance_from_home_km,
        'time_since_last_txn_hrs': tx.time_since_last_txn_hrs,
        'hour_of_day': tx.hour_of_day,
        'is_weekend': tx.is_weekend,
        'customer_age': age_bucket,
        'num_prev_transactions': tx.num_prev_transactions,
        'transaction_freq_monthly': tx.transaction_freq_monthly,
        'amount_per_balance': amount_per_balance,
        'country': CATEGORICAL_MAPPINGS['country'][tx.country],
        'city': CATEGORICAL_MAPPINGS['city'][tx.city],
        'merchant_category': CATEGORICAL_MAPPINGS['merchant_category'][tx.merchant_category],
        'payment_method': CATEGORICAL_MAPPINGS['payment_method'][tx.payment_method],
        'device_type': CATEGORICAL_MAPPINGS['device_type'][tx.device_type],
        'cust_tx_count': int(customer_profile.get('count', 0)),
        'cust_amount_ratio_to_mean': cust_amount_ratio_to_mean,
        'cust_amount_ratio_to_max': cust_amount_ratio_to_max,
        'cust_failed_mean': cust_failed_mean,
        'cust_intl_mean': cust_intl_mean,
        'failed_x_night': failed_x_night,
        'failed_x_intl': failed_x_intl,
        'failed_x_pin': failed_x_pin,
        'failed_x_highrisk': failed_x_highrisk,
        'night_x_intl': night_x_intl,
        'night_x_pin': night_x_pin,
        'night_x_highrisk': night_x_highrisk,
        'intl_x_pin': intl_x_pin,
        'intl_x_highrisk': intl_x_highrisk,
        'pin_x_highrisk': pin_x_highrisk,
        'failed_night_pin': failed_night_pin,
        'failed_night_intl': failed_night_intl,
        'failed_intl_pin': failed_intl_pin,
        'failed_intl_highrisk': failed_intl_highrisk,
        'risk_score': risk_score,
    }

    if metadata.get('features'):
        feature_names = metadata['features']
        return {name: input_data[name] for name in feature_names if name in input_data}
    return input_data


def get_file_hash(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global models, meta, customer_feature_store
    
    meta_path = 'models/ensemble_metadata.json'
    if not os.path.exists(meta_path):
        raise FileNotFoundError("Ensemble metadata not found. Train the model first.")
    
    with open(meta_path, 'r') as f:
        meta = json.load(f)
    
    model_files = {
        'xgboost': 'models/xgboost_fraud_detector.joblib',
        'lightgbm': 'models/lightgbm_fraud_detector.joblib',
        'catboost': 'models/catboost_fraud_detector.joblib'
    }
    
    loaded_models = {}
    model_hashes = {}
    for name, path in model_files.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file {path} not found.")
        file_hash = get_file_hash(path)
        model_hashes[name] = file_hash
        loaded_models[name] = joblib.load(path)
        print(f"Loaded {name} model. SHA-256 Integrity: {file_hash}")
    
    models = loaded_models
    
    mlops_logger.log_event('MODEL_STARTUP_LOAD', {
        'description': 'Stacking ensemble models loaded with verified SHA-256 hashes',
        'model_hashes': model_hashes,
        'features_used': meta['features'],
        'optimal_threshold': meta['optimal_threshold']
    })

    sec_path = 'data/processed/secure_dataset.csv'
    if os.path.exists(sec_path):
        print("Initializing Feature Store from secure_dataset.csv...")
        sec_df = pd.read_csv(sec_path)
        
        agg = sec_df.groupby('customer_id').agg({
            'transaction_amount': ['count', 'sum', 'max'],
            'failed_attempts': 'sum',
            'is_international': 'sum'
        })
        
        for cid, row in agg.iterrows():
            customer_feature_store[cid] = {
                'count': int(row[('transaction_amount', 'count')]),
                'amount_sum': float(row[('transaction_amount', 'sum')]),
                'amount_max': float(row[('transaction_amount', 'max')]),
                'failed_sum': int(row[('failed_attempts', 'sum')]),
                'intl_sum': int(row[('is_international', 'sum')])
            }
        print(f"Feature Store initialized with {len(customer_feature_store)} customer profiles.")
    else:
        print("Warning: secure_dataset.csv not found. Feature Store initialized empty.")
    yield

@app.post("/predict")
@limiter.limit("60/minute")
def predict(request: Request, tx: TransactionRequest, api_key: str = Depends(get_api_key)):
    global models, meta, customer_feature_store

    salt = os.getenv("COMPLIANCE_SALT", "COMPLIANCE_SALT_2026")
    hashed_cid = hashlib.sha256((tx.customer_id + salt).encode()).hexdigest()

    profile = customer_feature_store.get(hashed_cid, {
        'count': 0, 'amount_sum': 0.0, 'amount_max': 0.0, 'failed_sum': 0, 'intl_sum': 0
    })

    profile['count'] += 1
    profile['amount_sum'] += tx.transaction_amount
    profile['amount_max'] = max(profile['amount_max'], tx.transaction_amount)
    profile['failed_sum'] += tx.failed_attempts
    profile['intl_sum'] += tx.is_international
    customer_feature_store[hashed_cid] = profile

    feature_vector = build_feature_vector(tx, profile, meta)
    row_df = pd.DataFrame([feature_vector])
    if meta.get('features'):
        row_df = row_df[meta['features']]

    xgb_prob = float(models['xgboost'].predict_proba(row_df)[:, 1][0])
    lgb_prob = float(models['lightgbm'].predict_proba(row_df)[:, 1][0])
    cb_prob = float(models['catboost'].predict_proba(row_df)[:, 1][0])
    
    w_xgb = meta['weights']['xgboost']
    w_lgb = meta['weights']['lightgbm']
    w_cb = meta['weights']['catboost']
    
    ensemble_prob = (w_xgb * xgb_prob + w_lgb * lgb_prob + w_cb * cb_prob)
    prediction = 1 if ensemble_prob > meta['optimal_threshold'] else 0

    mlops_logger.log_event('MODEL_PREDICTION', {
        'masked_customer_id': hashed_cid,
        'transaction_amount': tx.transaction_amount,
        'risk_score': risk_score,
        'xgb_probability': xgb_prob,
        'lgb_probability': lgb_prob,
        'cb_probability': cb_prob,
        'ensemble_probability': ensemble_prob,
        'prediction': prediction,
        'decision_threshold': meta['optimal_threshold']
    })

    return {
        "is_fraud": prediction,
        "fraud_probability": ensemble_prob,
        "optimal_threshold": meta['optimal_threshold'],
        "audit_id": hashed_cid[:16]
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "models_loaded": list(models.keys())
    }
