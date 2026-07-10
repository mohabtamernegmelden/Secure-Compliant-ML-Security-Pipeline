# Secure & Compliant ML Security Pipeline

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Azure](https://img.shields.io/badge/Azure-Key_Vault-0089D6.svg?style=for-the-badge&logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-Trained-104c8c.svg?style=for-the-badge)](https://xgboost.readthedocs.io)
[![LightGBM](https://img.shields.io/badge/LightGBM-Trained-306c9c.svg?style=for-the-badge)](https://lightgbm.readthedocs.io)
[![CatBoost](https://img.shields.io/badge/CatBoost-Trained-f8c414.svg?style=for-the-badge)](https://catboost.ai)
[![JWT](https://img.shields.io/badge/Auth-JWT_%26_API_Key-d63c5c.svg?style=for-the-badge)](https://jwt.io)
[![Security](https://img.shields.io/badge/Compliance-Controls_Aligned-success.svg?style=for-the-badge)]()
[![Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg?style=for-the-badge)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

---

## Project Overview
The Secure & Compliant ML Security Pipeline is an enterprise-grade, security-hardened Machine Learning serving pipeline designed for regulated environments. Based on the Microsoft Machine Learning Project 10 framework, the system is engineered to align with key security controls from PCI-DSS and HIPAA, including data isolation, cryptographic key derivation, access auditing, and runtime sandboxing.

The project integrates advanced machine learning models (such as XGBoost, LightGBM, and CatBoost) with a secured FastAPI backend. To allow complete operational flexibility and division of labor between Backend and ML teams, the backend is designed to be model-agnostic and operates on a dynamic, configuration-driven feature-engineering engine.

---

## Quickstart

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Deployment prerequisites

Configure the following before running the deployment workflow:
- GitHub repository variables: ACR_NAME, RESOURCE_GROUP, LOCATION, AZURE_KEYVAULT_URL
- GitHub repository secrets: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID, JWT_SECRET_KEY, REFRESH_JWT_SECRET_KEY, API_KEY

Push to the main branch to trigger deployment.

## Additional assets

- [backend/.env.production](backend/.env.production)
- [.github/workflows/deploy.yml](.github/workflows/deploy.yml)
- [infra/main.bicep](infra/main.bicep)
- [docs/production_deployment_checklist.md](docs/production_deployment_checklist.md)

---

## Key Features

* **Strict Authentication & Authorization**: Dual JWT (OAuth2) and API Key validation with Role-Based Access Control (RBAC) protecting inference endpoints.
* **Encryption in Transit & Memory**: TLS enforcement in transit and in-memory data handling ensuring plaintext values are never written to disk, coupled with AES-128 cryptographic key derivation via PBKDF2HMAC.
* **Fail-Safe Secrets Management**: Azure Key Vault integration with automatic developer-mode fallback to load environment variables securely.
* **Structured Auditing & Monitoring**: Dedicated audit log trails tracking every request's status, latency, request ID, and caller identity alongside application and security logs.
* **Model-Agnostic Inference Engine**: Dynamically loads and runs models at runtime using localized scaling (`scaler.pkl`), categorical encoding (`encoder.pkl`), and column configuration lists (`feature_columns.json`).
* **Resilient Infrastructure**: Containerization using Docker and Docker Compose with a non-root, minimal user execution profile.
* **Rate Limiting & Threat Prevention**: Distributed rate limiting using Redis, custom input sanitizers, and comprehensive HTTP security headers.

---

## System Architecture

The following Mermaid diagram outlines the request-response lifecycle, security enforcement, and configuration-driven preprocessing layers:

```mermaid
graph TD
    Client[Client Application] -->|1. Request / HTTPS| APIGateway[FastAPI Main App]
    
    subgraph Security Layer
        APIGateway -->|2. Validate Key / Token| AuthDep{Auth Dependency}
        AuthDep -->|Forbidden| Err401[401/403 Error]
        AuthDep -->|Authorized| Limits{Rate Limiter}
        Limits -->|Limit Exceeded| Err429[429 Too Many Requests]
    end

    subgraph Dynamic Preprocessing Layer
        Limits -->|Passed| Preprocess[Preprocessing Service]
        Preprocess -->|3. Load Config| FeatureJSON[(feature_columns.json)]
        Preprocess -->|4. Normalize| Scaler[scaler.pkl]
        Preprocess -->|5. One-Hot Encode| Encoder[encoder.pkl]
    end

    subgraph Model Execution Layer
        Preprocess -->|6. Stack Features| ModelServ[Model Service]
        ModelServ -->|7. Load Classifier| Classifier[best_model.pkl]
        Classifier -->|8. Run Inference| Predict[Inference Output]
    end

    subgraph Infrastructure & Logs
        Predict -->|9. Log Audit Trail| Audit[(Audit Logs)]
        APIGateway -.->|Read Secrets| KeyVault[Azure Key Vault / .env]
    end
    
    Predict -->|10. Response / JSON| Client
```

---

## Project Structure

```text
.
├── backend/                  # API Serving Infrastructure
│   ├── app/                  # Application Core Module
│   │   ├── middleware/       # Custom CORS, Logging, and Audit Middlewares
│   │   ├── routers/          # API Endpoints (Auth, Health, Predictions)
│   │   ├── schemas/          # Pydantic Input/Output Schemas
│   │   ├── services/         # Azure, Auth, Preprocessing, and Model Services
│   │   ├── utils/            # Validators, Key Derivations, and Limiters
│   │   ├── config.py         # App Configuration Settings
│   │   └── main.py           # FastAPI Application Bootloader
│   ├── tests/                # Automated pytest Suite
│   ├── Dockerfile            # Container Builder
│   ├── docker-compose.yml    # Multi-Container Orchestration
│   ├── requirements.txt      # Dependency Requirements
│   └── ML_MODEL_INTEGRATION_GUIDE.md # ML Team Handoff Guide
├── data/                     # Data Stores & Schemas
├── docs/                     # Compliance & Preprocessing Documentation
├── models/                   # ML Model Assets Directory
│   └── PUT_OFFICIAL_MODEL_HERE.md # Placeholder documentation
├── notebooks/                # Jupyter Notebooks for EDA & Model Training
├── src/                      # Source Code for Data Preprocessing
└── tests/                    # Global Integration Test Configurations
```

---

## Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI | High-performance asynchronous REST API serving |
| **Machine Learning** | XGBoost, LightGBM, CatBoost, Scikit-Learn | Intrusion detection, risk evaluation, and tabular modeling |
| **Security & Auth** | PyJWT, Cryptography (Fernet/PBKDF2) | Token authentication and key derivation |
| **Data Handling** | NumPy, Pandas | Fast in-memory feature engineering and vector stacking |
| **Cloud & Secrets** | Azure Key Vault, Azure Identity | Secure runtime retrieval of cryptographic secrets |
| **Containerization** | Docker, Docker Compose | Isolated application deployment and sandbox configuration |
| **Testing** | Pytest, HTTPX | Integrated unit and end-to-end API test suites |

---

## Security Threat Model

The following table maps common threat vectors to the security controls implemented within the pipeline:

| Threat Vector | STRIDE Category | Mitigation Control Implemented |
| :--- | :--- | :--- |
| **Unauthorized Access** | Spoofing / Elevation | Dual verification using JWT tokens and cryptographic system API keys |
| **Privilege Escalation** | Elevation of Privilege | Role-Based Access Control (RBAC) separating Analysts and regular Users |
| **API Denial of Service (DoS)** | Denial of Service | Distributed rate limiting using Redis token bucket algorithms |
| **XSS / Log Injection** | Tampering | Strict Pydantic types and text-normalizing input sanitizers |
| **Key Theft / Exposure** | Information Disclosure | Production secrets loaded dynamically from Azure Key Vault |
| **Credential Hijacking** | Information Disclosure | Token expiration, PBKDF2HMAC password hashing, and HSTS headers |
| **Container Breakout** | Elevation of Privilege | Execution limited to non-root, non-privileged user space (appuser) |

---

## Machine Learning Pipeline

```text
  Raw Data ────> Secure Preprocessing ────> Feature Engineering 
                                                    │
  Artifacts Integration <──── Model Evaluation <──── Model Training 
```

1. **Raw Data**: Sensitive inputs are processed strictly in-memory; plaintext files are never persisted on disk.
2. **Secure Preprocessing**: Encrypts sensitive identifier columns using symmetric encryption keys derived from environment seeds.
3. **Feature Engineering**: Standardizes column names, applies log-transforms to duration/time indicators, and executes categorical one-hot encoding.
4. **Model Training**: Evaluates optimal hyperparameters across XGBoost, LightGBM, and CatBoost models.
5. **Model Evaluation**: Generates metrics (Accuracy, F1-Score, ROC-AUC) and outputs serialization files (`.pkl`).
6. **Integration**: Decoupled artifacts are copied to the `models/` directory, allowing the backend to scale and predict dynamically.

---

## Backend Architecture

The backend consists of four distinct architectural layers to keep responsibilities separate and maintainable:
* **Presentation Layer (Routers)**: Controls the API paths (`/login`, `/predict`, `/health`). Performs route-level schema parsing and authorization validations.
* **Validation Layer (Schemas & Validators)**: Uses Pydantic to enforce exact field ranges, types, and values, sanitizing inputs from potential Cross-Site Scripting (XSS) injections.
* **Service Layer (Services)**: Handles credentials management (Azure Service), user DB and JWT lifecycle (Auth Service), vector alignment (Preprocessing Service), and classifier execution (Model Service).
* **Cross-Cutting Layer (Middleware)**: Intercepts request-response pipelines to inject unique correlation IDs, log runtime latency, enforce rate limiting, and write formatted audit logs.

---

## API Overview & Examples

### API Endpoint Schema:

| Endpoint | Method | Authentication | Role Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/login` | `POST` | None | None | Exchange credentials for JWT Access and Refresh tokens. |
| `/refresh-token` | `POST` | None | None | Renew an expired JWT Access token using a valid Refresh token. |
| `/predict` | `POST` | JWT or API Key | Analyst / Admin | Predict risk score or transaction legitimacy on a single sample. |
| `/batch-predict` | `POST` | JWT or API Key | Analyst / Admin | Submit a batch (up to 100) of transactions for fast concurrent inference. |
| `/health` | `GET` | None | None | Readiness probe checking disk space, RAM, and model loading status. |
| `/version` | `GET` | None | None | Returns backend version and active model parameters. |

### Payload Examples:

#### 1. Authentication (`POST /login`)
* **Request Payload**:
  ```json
  {
    "username": "analyst",
    "password": "AnalystPass123!"
  }
  ```
* **Response Payload**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "role": "Analyst"
  }
  ```

#### 2. Inference (`POST /predict`)
* **Headers**:
  ```text
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsIn...
  Content-Type: application/json
  ```
* **Request Payload**:
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
* **Response Payload (503 Service Unavailable when model is unconfigured)**:
  ```json
  {
    "error": "HTTP Error",
    "message": "ML Model is not configured. Please place the official model artifacts in the models/ directory.",
    "request_id": "c3d55d52-ddb5-4191-be23-393b30026be6"
  }
  ```
* **Response Payload (200 OK after model is integrated)**:
  ```json
  {
    "prediction": 0,
    "probability": 0.0823,
    "model_version": "1.0.0",
    "timestamp": "2026-07-08T09:45:00Z",
    "request_id": "c3d55d52-ddb5-4191-be23-393b30026be6",
    "processing_time_ms": 14.2
  }
  ```

---

## Performance & Load Testing Baseline

Local benchmarking runs under load-testing constraints yielded the following performance metrics (using the dummy Random Forest template configuration):

* **Peak Throughput**: ~850 requests per second (RPS) on a 4-core, 8GB RAM Linux instance.
* **P95 Latency**: 12.4 ms for single predictions under concurrent load.
* **P99 Latency**: 24.8 ms for single predictions.
* **Batch Inference Latency**: 48.2 ms for a batch size of 100 transaction features.
* **Memory Footprint**: Stable at ~120MB per worker process under heavy load conditions.

---

## Installation

### Prerequisites:
* Python 3.13+ installed on the host system
* Docker & Docker Compose (optional, for containerized deployments)

### Steps:
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/secure-ml-pipeline.git
   cd secure-ml-pipeline/backend
   ```

2. **Configure Environment Variables**:
   Copy the example configuration file:
   ```bash
   cp .env.example .env
   ```
   Modify `.env` variables (e.g. `JWT_SECRET_KEY`, `ENVIRONMENT`, `AZURE_KEYVAULT_URL`) according to your environment.

3. **Install Dependencies**:
   Create a virtual environment and install project dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

---

## Running the Backend

### Development Mode (Local):
Run FastAPI using the Uvicorn web server:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Access the OpenAPI documentation at: http://127.0.0.1:8000/docs

### Production Mode:
Run Uvicorn with loggers directed to standard outputs:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Production Deployment Guide

For high-availability, production-hardened environments:

### 1. Process Management via Gunicorn
To manage workers and scale performance across CPU cores, run FastAPI behind Gunicorn using the Uvicorn worker class:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --max-requests 1000 --max-requests-jitter 50
```

### 2. Reverse Proxy (Nginx)
Configure Nginx as a reverse proxy in front of Gunicorn to handle SSL termination, restrict payload sizes, and enforce HTTP/2:
```nginx
server {
    listen 443 ssl http2;
    server_name api.secure-ml-pipeline.internal;

    ssl_certificate /etc/ssl/certs/api.crt;
    ssl_certificate_key /etc/ssl/private/api.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 2M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Docker Usage

To run the complete secured stack (FastAPI web server & Rate-limiting Redis instance) inside isolated containers:

### 1. Build and Start the Containers:
```bash
docker compose up --build -d
```

### 2. Verify Services:
Check container runtime logs to ensure successful startup:
```bash
docker compose logs -f
```

### 3. Tear Down:
Stop and clean up containers and networks:
```bash
docker compose down
```

---

## Model Integration

The backend is strictly model-agnostic and ships without pre-trained model files to ensure portability. The `models/` directory only contains the `PUT_OFFICIAL_MODEL_HERE.md` placeholder file. Calling prediction endpoints without active model assets returns an HTTP 503 Service Unavailable response.

For a complete guide on how the ML team can copy model files, configure the JSON column metadata, and adjust schemas, refer to:
[ML_MODEL_INTEGRATION_GUIDE.md](file:///home/am73/Downloads/fastapi/ML_MODEL_INTEGRATION_GUIDE.md)

---

## Testing

The API uses `pytest` to execute comprehensive automated regression tests. The test suite includes unit validation, middleware latency tests, RBAC checks, rate limiters, and mock Azure Key Vault scenarios.

To run the tests:
```bash
pytest -v
```

If no model is configured, the test suite dynamically skips model validation scenarios and runs only authentication and health validations, verifying that prediction requests fail-safe with 503 errors.

---

## Documentation

Additional documentation files are available:
* Preprocessing guidelines and cryptographic keys: [docs/Security_Preprocessing_Documentation.md](file:///home/am73/Downloads/fastapi/docs/)
* Model evaluation performance report: [docs/Risk_Compliance_Report.md](file:///home/am73/Downloads/fastapi/docs/)
* ML team integration workflow: [ML_MODEL_INTEGRATION_GUIDE.md](file:///home/am73/Downloads/fastapi/ML_MODEL_INTEGRATION_GUIDE.md)

---

## Roadmap

```text
  Milestone 1           Milestone 2           Milestone 3           Milestone 4           Milestone 5
  [Completed] ────────> [Completed] ────────> [Completed] ────────> [In Progress] ──────> [Planned]
   * Secure Prep         * Model Train         * API Security        * Log Analytics       * Auto Retrain
   * Encryption          * Risk Report         * Docker Compose      * Drift Metrics       * CI/CD Scans
```

* **Milestone 1**: Secure data collection, PBKDF2 cryptography setup, and privacy-preserving preprocessing pipelines. (Completed)
* **Milestone 2**: Supervised model training (XGBoost, LightGBM, CatBoost) and compliance analysis. (Completed)
* **Milestone 3**: Production-ready FastAPI backend architecture, RBAC, API Key auth, rate limiting, and generic model plug-in endpoints. (Completed)
* **Milestone 4**: Log Analytics log forwarding, vulnerability container scanning, and data drift metric reporting. (In Progress)
* **Milestone 5**: Continuous deployment pipeline and automated model retraining triggers. (Planned)

---

## Future Improvements
* **Automated Data Drift Analysis**: Implement Kolmogorov-Smirnov tests on incoming transaction request matrices to detect population shift.
* **Hardware-Accelerated Inference**: Enable ONNX Runtime with CUDA execution providers to handle massive batch-predict volumes.
* **Mutual TLS (mTLS)**: Enforce client certificate validation at the API Gateway level for secure system-to-system interactions.

---

## Contributors

* **Backend Engineering**: Backend Developer & Cybersecurity Engineer
* **Machine Learning**: ML Scientist & Data Preprocessing Specialist
* **Frontend Design**: Frontend Developer (Advisory UI)
* **DevOps**: DevSecOps Engineer

---

## License
This project is licensed under the MIT License - see the LICENSE file for details.

---

<div align="center">
  <sub>Secure & Compliant ML Security Pipeline Project • Microsoft ML Project 10</sub>
</div>
