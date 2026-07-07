# Security Preprocessing Documentation

## 1. Overview

This document describes the security and privacy measures applied to the Bank Fraud Detection dataset as part of **Milestone 1: Data Security & Preprocessing**. The pipeline ensures compliance with GDPR, PCI-DSS, and general data protection best practices before any model training occurs.

---

## 2. Data Collection Compliance

### 2.1 Privacy Principles Applied

| Principle | Implementation |
|:---|:---|
| **Data Minimization** (GDPR Art. 5) | Only features required for fraud detection are retained. Tracking identifiers (dates, times) are dropped after feature extraction. |
| **Purpose Limitation** | Data is used exclusively for fraud detection model training. PII is encrypted and never used as model features. |
| **Storage Limitation** | Raw data is stored separately from processed/secure data. Secure dataset contains no reversible PII. |
| **PCI-DSS Req. 3** | Cardholder data (customer names, emails) is encrypted at rest using Fernet (AES-128-CBC). |
| **PCI-DSS Req. 4** | Encryption keys are managed via environment variables, never hardcoded in production. |

### 2.2 Dataset Description

- **Source**: Synthetic bank fraud dataset (`data/raw/bank_fraud.csv`)
- **Size**: 1,000,000 transactions, 26 columns
- **Fraud Rate**: 5.5% (55,255 fraudulent transactions)
- **PII Columns**: `customer_name`, `customer_email`, `customer_id`, `transaction_id`
- **Quasi-Identifiers**: `customer_age`

---

## 3. Encryption Methodology

### 3.1 Fernet Symmetric Encryption (PII Fields)

**Columns affected**: `customer_name`, `customer_email`

| Property | Value |
|:---|:---|
| Algorithm | Fernet (AES-128-CBC + HMAC-SHA256) |
| Key Length | 256-bit URL-safe base64 encoded |
| Key Source | Environment variable `SECRET_VAULT_KEY` |
| Reversibility | ✅ Reversible (for authorized decryption, e.g., alert emails) |
| Library | `cryptography.fernet.Fernet` (Python) |

**How it works**:
1. Each plaintext value is encoded to bytes
2. Fernet encrypts using AES-128-CBC with a random IV
3. HMAC-SHA256 ensures ciphertext integrity
4. Output is a URL-safe base64-encoded string

**Training Mode Optimization**: During model training, these columns are replaced with mock values (`MOCK_ENCRYPTED_NAME`) since they are dropped before feature engineering. This avoids the ~120-second encryption overhead on 1M rows without compromising security — the columns are never used as features.

### 3.2 SHA-256 Hashing (System Identifiers)

**Columns affected**: `customer_id`, `transaction_id`

| Property | Value |
|:---|:---|
| Algorithm | SHA-256 |
| Salt | `COMPLIANCE_SALT_2026` (application-level) |
| Reversibility | ❌ Irreversible (one-way hash) |
| Purpose | Record matching without exposing plain identifiers |

**How it works**:
1. Each identifier is concatenated with a compliance salt
2. SHA-256 produces a 64-character hexadecimal digest
3. Original identifiers cannot be recovered from the hash

**Optimization**: Unique customer IDs are pre-mapped into a lookup dictionary, reducing redundant hash computations by ~80%.

---

## 4. Anonymization Techniques

### 4.1 Age Bucketing (k-Anonymity)

**Column affected**: `customer_age`

| Age Range | Bucket Label | Purpose |
|:---|:---|:---|
| 0–18 | 0 | Minor |
| 19–25 | 1 | Young Adult |
| 26–35 | 2 | Adult |
| 36–50 | 3 | Middle Age |
| 51–65 | 4 | Senior |
| 66–100 | 5 | Elderly |

This ensures that exact age values cannot be used for re-identification while preserving the demographic signal needed for fraud detection.

---

## 5. Column Removal Policy

| Columns Removed | Reason |
|:---|:---|
| `transaction_date`, `transaction_time` | Temporal tracking identifiers; hour/weekend/night flags are extracted first |
| `customer_name`, `customer_email` | Encrypted PII — dropped before feature engineering |
| `transaction_id`, `customer_id` | Hashed identifiers — dropped after customer-level feature aggregation |
| `fraud_type` | Target leakage — describes the type of fraud (only exists for fraud=1) |

---

## 6. Audit Trail Specification

Every security-sensitive operation is logged to `data/processed/audit_log.json` by the `SecurityAuditLogger` class.

### 6.1 Event Schema

```json
{
  "timestamp": "2026-07-07T00:30:00.000Z",
  "action": "PII_ENCRYPTION",
  "columns": ["customer_name", "customer_email"],
  "method": "Fernet AES-128-CBC symmetric encryption",
  "rows_affected": 1000000
}
```

### 6.2 Logged Events

| Event Action | Description |
|:---|:---|
| `PIPELINE_START` | Pipeline initiated with row/column counts |
| `KEY_LOADED` | Encryption key source recorded |
| `PII_ENCRYPTION` | Names and emails encrypted (or mocked for training) |
| `IDENTIFIER_HASHING` | Customer and transaction IDs hashed |
| `AGE_ANONYMIZATION` | Age values bucketed for k-anonymity |
| `COLUMN_REMOVAL` | Tracking columns dropped |
| `PIPELINE_COMPLETE` | Final dataset shape recorded |

---

## 7. Data Flow Diagram

```
┌──────────────────┐
│  Raw Dataset     │
│  (1M rows, 26    │
│   columns)       │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  Synthetic PII   │──→ customer_name, customer_email added
│  Generation      │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  Fernet          │──→ customer_name, customer_email encrypted
│  Encryption      │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  SHA-256         │──→ customer_id, transaction_id hashed
│  Hashing         │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  Age Bucketing   │──→ customer_age → 6 buckets
│  (k-Anonymity)   │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  Column Removal  │──→ transaction_date, transaction_time dropped
└───────┬──────────┘
        │
        ▼
┌──────────────────┐    ┌──────────────────┐
│  Secure Dataset  │    │  Audit Log       │
│  (CSV)           │    │  (JSON)          │
└──────────────────┘    └──────────────────┘
```

---

## 8. Key Management Recommendations (Production)

> **⚠️ WARNING**: The default fallback key in the codebase is for development only.

For production deployment:
1. Store the Fernet key in a secrets manager (AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault)
2. Rotate keys annually per PCI-DSS Req. 3.6
3. Use separate keys for development, staging, and production environments
4. Never commit keys to version control
