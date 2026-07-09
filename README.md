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
app/
├── __init__.py
├── main.py                    # Single-file application entrypoint containing the entire backend implementation
├── config.py                  # Legacy configuration module (not imported by app/main.py)
├── dependencies.py            # Legacy auth helper module (not imported by app/main.py)
├── middleware/
│   ├── __init__.py
│   ├── cors.py                # Legacy CORS helper module (not imported by app/main.py)
│   └── logging.py             # Legacy audit logging helper module (not imported by app/main.py)
├── routers/
│   ├── __init__.py
│   ├── auth.py                # Legacy auth router (not imported by app/main.py)
│   ├── health.py              # Legacy health router (not imported by app/main.py)
│   └── predict.py             # Legacy prediction router (not imported by app/main.py)
├── schemas/
│   ├── __init__.py
│   ├── auth.py                # Legacy authentication models (not imported by app/main.py)
│   ├── prediction.py          # Legacy validation models (not imported by app/main.py)
│   └── security.py            # Legacy schema helpers (not imported by app/main.py)
├── services/
│   ├── __init__.py
│   ├── auth_service.py        # Legacy token/auth helper (not imported by app/main.py)
│   ├── azure_service.py       # Legacy Key Vault helper (not imported by app/main.py)
│   ├── logging_service.py     # Legacy logging helpers (not imported by app/main.py)
│   ├── model_service.py       # Legacy model loader helper (not imported by app/main.py)
│   └── preprocessing_service.py # Legacy preprocessing helper (not imported by app/main.py)
├── utils/
│   ├── __init__.py
│   ├── security.py            # Legacy encryption helper (not imported by app/main.py)
│   └── validators.py          # Legacy input sanitization helper (not imported by app/main.py)
models/
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
   cd Secure-Compliant-ML-Security-Pipeline
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

For a full walkthrough covering local startup, Docker usage, and Azure deployment steps, see [docs/production_usage_and_azure_deployment.md](docs/production_usage_and_azure_deployment.md).
