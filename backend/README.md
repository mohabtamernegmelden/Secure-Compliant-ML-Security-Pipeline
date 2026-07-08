# Secure & Compliant ML Security Pipeline Backend

A production-ready, enterprise-grade FastAPI backend designed for regulated environments (finance, healthcare). This backend exposes secure inference APIs, implements robust authentication, integrates with Azure Key Vault, and executes comprehensive audit and security logging.

---

## Features
- **FastAPI Core**: Highly performant, async-ready inference endpoints with automatic Swagger documentation.
- **Enterprise-Grade Security**:
  - Role-Based Access Control (RBAC): `Admin`, `Analyst`, `User` roles.
  - JWT Authentication: Access token (15 mins) and Refresh token (7 days) rotation.
  - API Key Auth: Service-to-service header checking (`X-API-Key`).
  - Security Headers: Configured with CORS, CSP, HSTS, X-Frame-Options, X-Content-Type-Options, and Referrer Policy.
  - Rate Limiting: Built-in request throttle (100 requests / 60 seconds per IP).
  - No Information Leakage: custom exception handlers return generic error bodies with correlation request IDs, masking stack traces from external exposure.
- **Azure Key Vault Integration**: Resolves environment configurations and keys securely at startup, falling back to local configurations for local development.
- **Structured Auditing & Logging**:
  - Independent JSON structured logs for: Application, Security, Audit, and Errors.
  - Request tracking utilizing a correlation `X-Request-ID` across all transactions and logs.
- **Robust Preprocessing**: Standardized scaling and encoding pipeline managed once at startup.

---

## Project Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Application entrypoint & middlewares
│   ├── config.py                  # Pydantic Settings & Azure Key Vault
│   ├── dependencies.py            # Authentication & RBAC dependencies
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── cors.py                # CORS configuration
│   │   └── logging.py             # Correlation ID & request logging
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                # JWT endpoints (/login, /refresh-token)
│   │   ├── health.py              # Health check & versioning
│   │   └── predict.py             # Inference endpoints (/predict, /batch-predict)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                # Authentication models
│   │   ├── prediction.py          # Input/output validation models
│   │   └── security.py            # Standard log formatting schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py        # Token operations & authentication
│   │   ├── azure_service.py       # Key Vault connector
│   │   ├── logging_service.py     # Structured logging instances
│   │   ├── model_service.py       # Model loader & inference executor
│   │   └── preprocessing_service.py # Feature transformation pipeline
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── security.py            # Symmetric encryption at rest
│   │   └── validators.py          # Input sanitization helper functions
├── models/
│   ├── best_model.pkl             # Serialized ML model
│   ├── scaler.pkl                 # Numerical feature scaler
│   ├── encoder.pkl                # Categorical feature encoder
│   └── feature_columns.json       # Feature configuration metadata
├── logs/                          # Directory for structured JSON logs
├── scripts/
│   └── generate_dummy_models.py   # Script to generate dummy model assets
├── tests/
│   └── test_backend.py            # Integration test suite
├── Dockerfile                     # Multi-stage secure runner
├── docker-compose.yml             # Orchestration compose file
├── requirements.txt               # Application dependencies
└── .env.example                   # Environment configuration template
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- Docker & Docker Compose (optional)

### Setup & Installation
1. Clone the repository and navigate to the project directory:
   ```bash
   cd fastapi
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to configure your custom JWT secrets and optional Azure Key Vault URL.*

5. (Optional) Generate the dummy model assets for testing:
   ```bash
   python3 scripts/generate_dummy_models.py
   ```

---

## Running Locally

To start the development server with hot-reloading:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to view the interactive API docs (Swagger UI).

---

## Running in Docker

To build and run the containerized backend:
```bash
docker-compose up --build
```
This builds a secure multi-stage container running as a non-privileged `mluser` and binds the container's logs to your local `logs/` directory for analysis.

---

## API Documentation

### Authentication Flow
1. **Login**
   - **Endpoint**: `POST /login`
   - **Payload**:
     ```json
     {
       "username": "analyst",
       "password": "AnalystPass123!"
     }
     ```
   - **Response**: Returns `access_token`, `refresh_token`, and the assigned user role.

2. **Refresh Token**
   - **Endpoint**: `POST /refresh-token`
   - **Payload**:
     ```json
     {
       "refresh_token": "<refresh_token_string>"
     }
     ```
   - **Response**: Returns a new access token and a rotated refresh token.

### Inference Endpoints (Protected)
Both endpoints require the header `Authorization: Bearer <access_token>` with an **Analyst** or **Admin** role.

1. **Single Predict**
   - **Endpoint**: `POST /predict`
   - **Payload**:
     ```json
     {
       "age": 35,
       "income": 75000.0,
       "transaction_amount": 120.50,
       "risk_score": 0.23,
       "department": "finance",
       "user_role": "user"
     }
     ```
   - **Response**:
     ```json
     {
       "prediction": 0,
       "probability": 0.15,
       "model_version": "1.0.0",
       "timestamp": "2026-07-08T03:15:00Z",
       "request_id": "c1f73b88-1c4b-4b10-8b17-02458a2f4d6d",
       "processing_time_ms": 1.25
     }
     ```

2. **Batch Predict**
   - **Endpoint**: `POST /batch-predict`
   - **Payload**:
     ```json
     {
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
     ```

---

## Azure Deployment

To deploy this container to Azure App Service:
1. Push the Docker image to Azure Container Registry (ACR):
   ```bash
   docker tag ml-security-pipeline-backend:latest myregistry.azurecr.io/ml-backend:v1
   docker push myregistry.azurecr.io/ml-backend:v1
   ```
2. Set up Azure App Service to run the container.
3. Configure Managed Identity on the App Service.
4. Grant Key Vault secrets permissions to the App Service's principal.
5. Set `AZURE_KEYVAULT_URL` in the App Service Configuration. The app will automatically connect and load secrets.
