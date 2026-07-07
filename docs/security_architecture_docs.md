# Security Architecture Documentation

## 1. Threat Modeling (STRIDE Analysis)

We analyzed the deployment architecture of the Fraud Detection service using the Microsoft STRIDE framework to ensure secure deployment.

| Threat Category | Description | Mitigation in API (`src/app.py`) |
|:---|:---|:---|
| **Spoofing Identity** | An attacker submits predictions pretending to be an authorized client application. | **API Key Authentication**: Header-based authentication (`X-API-Key`) enforces identity verification. In production, this shifts to Azure Active Directory OAuth2 flow. |
| **Tampering with Data** | An attacker intercepting network transit modifies transaction data or features to bypass detection. | **HTTPS Enforcement**: TLS encryption ensures complete data integrity in transit. **Pydantic Validation**: Strong schemas prevent SQL/code injection attacks. |
| **Repudiation** | An attacker disputes making transactions or administrative model operations. | **Audit Logs**: Every prediction event and key access is logged to `mlops_audit_log.json` with hash mapping, providing non-repudiation. |
| **Information Disclosure** | Attackers intercepting logs see plain customer emails, names, or cleartext transaction records. | **Hashing/Masking**: Identifiers are irreversible SHA-256 hashes (`COMPLIANCE_SALT_2026`). Plain values are omitted from the logs. |
| **Denial of Service (DoS)** | A malicious client floods the system with requests to crash the API server. | **Rate Limiting Middleware**: `SlowAPI` enforces client-level rate limiting (configured to 60 req/min). |
| **Elevation of Privilege** | Users access administrative metrics or model version controls. | **Role-Based Access Control (RBAC)**: Enforced via API routes. Key Vault permissions restrict model loading keys to authorized Managed Identities. |

---

## 2. Infrastructure Architecture (Azure Alignment)

```
                            ┌────────────────────────┐
                            │      Azure WAF         │ (Web Application Firewall)
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │    Azure API Gateway   │ (API Management - TLS, Rate Limit)
                            └───────────┬────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────┼────────────────────────────────────────┐
│ Virtual Network (VNet)                │ Private Endpoint                       │
│                                       ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                     Azure App Service (FastAPI Container)                 │  │
│  │                                                                          │  │
│  │  Managed Identity                                                        │  │
│  │         │                                                                │  │
│  └─────────┼────────────────────────────────────────────────────────────────┘  │
│            │ (Token Access via DefaultAzureCredential)                          │
│            ▼                                                                   │
│  ┌─────────────────────────────────┐                                           │
│  │  Azure Key Vault                │                                           │
│  │  - SECRET-VAULT-KEY             │                                           │
│  │  - FRAUD-DETECTION-API-KEY       │                                           │
│  └─────────────────────────────────┘                                           │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Managed Identities (Passwordless Authentication)
To completely eliminate hardcoded secrets, production deployment relies on Azure **System-Assigned Managed Identity**:
1. The Azure App Service (hosting the FastAPI container) is assigned a cryptographic identity within Microsoft Entra ID.
2. The App Service attempts to load the secret key on startup using `DefaultAzureCredential()` without needing passwords or client secrets.
3. Azure Key Vault access policies allow only this Managed Identity to read secrets (`GetSecret` permissions).

### 2.2 Endpoint Hardening Strategies
- **TLS 1.3 Encryption**: Ensures all client-server communications are encrypted.
- **Pydantic Schema Guard**: Rejects payloads containing structural anomalies, preventing parsing-based overflow or injection attacks.
- **IP Rate Limiting**: The server returns `429 Too Many Requests` when limits are breached, preserving server capacity.
- **WAF Rules (OWASP Top 10)**: Prevents SQL injections, Cross-Site Scripting (XSS), and automated brute force bots.
- **Model Lineage Auditing**: The service calculates the SHA-256 hash of the loaded model binaries (`xgboost_fraud_detector.joblib`, etc.) and prints them to logs on startup to prevent model hijacking.
