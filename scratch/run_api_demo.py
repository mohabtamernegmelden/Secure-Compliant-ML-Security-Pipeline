import os
import time
import subprocess
import requests
import json
import sys

# Port for demo FastAPI server
PORT = 8000
API_URL = f"http://127.0.0.1:{PORT}"
API_KEY = "FRAUD_DETECTION_SECURE_API_KEY_2026"

print("=== STARTING FRAUD DETECTION API DEMO ===")

# 1. Spawn FastAPI server in background
print("Spawning FastAPI server using uvicorn...")
server_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.app:app", "--port", str(PORT), "--host", "127.0.0.1"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Wait for server to boot up
time.sleep(4)

# Check if server is running
if server_process.poll() is not None:
    print("[ERROR] FastAPI server failed to start. Standard error:")
    stderr = server_process.stderr.read()
    print(stderr)
    sys.exit(1)

print("FastAPI server successfully started in background.")

try:
    # 2. Check Health Endpoint
    print("\n--- Testing GET /health ---")
    resp = requests.get(f"{API_URL}/health")
    print(f"Response ({resp.status_code}):", resp.json())

    # 3. Test prediction payload
    test_transaction = {
        "customer_id": "CUST_TEST_001",
        "failed_attempts": 3,
        "is_night_transaction": 1,
        "is_international": 1,
        "pin_changed_recently": 1,
        "merchant_category": "Jewelry",
        "transaction_amount": 1250.00,
        "account_balance": 15000.00,
        "credit_score": 710,
        "distance_from_home_km": 15.5,
        "time_since_last_txn_hrs": 2.5,
        "hour_of_day": 3,
        "is_weekend": 1,
        "customer_age": 34,
        "num_prev_transactions": 142,
        "transaction_freq_monthly": 18,
        "country": "USA",
        "city": "Los Angeles",
        "payment_method": "Credit Card",
        "device_type": "Mobile"
    }

    # 4. Authorized request (with X-API-Key)
    print("\n--- Testing Authorized POST /predict ---")
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    resp = requests.post(f"{API_URL}/predict", json=test_transaction, headers=headers)
    print(f"Response ({resp.status_code}):")
    print(json.dumps(resp.json(), indent=2))

    # 5. Unauthorized request (invalid key)
    print("\n--- Testing Unauthorized POST /predict ---")
    bad_headers = {"X-API-Key": "INVALID_KEY", "Content-Type": "application/json"}
    resp = requests.post(f"{API_URL}/predict", json=test_transaction, headers=bad_headers)
    print(f"Response ({resp.status_code}):", resp.json())

    # 6. Test Rate Limiting (send fast requests)
    print("\n--- Testing Rate Limiting (DDoS prevention) ---")
    print("Sending 65 requests rapidly to trigger rate limit (configured limit: 60/minute)...")
    throttled = False
    for i in range(70):
        resp = requests.post(f"{API_URL}/predict", json=test_transaction, headers=headers)
        if resp.status_code == 429:
            print(f"  Rate limiting triggered at request {i+1}! Response: {resp.json()}")
            throttled = True
            break
    if not throttled:
        print("  Warning: Rate limit was not hit. Check API configuration.")

    # 7. Print generated MLOps logs
    log_path = 'data/processed/mlops_audit_log.json'
    print(f"\n--- Checking MLOps Audit Logs ({log_path}) ---")
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            logs = json.load(f)
        print(f"Total events in log: {len(logs)}")
        print("Latest prediction event log entry:")
        pred_logs = [log for log in logs if log['action'] == 'MODEL_PREDICTION']
        if pred_logs:
            print(json.dumps(pred_logs[-1], indent=2))
        else:
            print("No prediction logs found.")
    else:
        print(f"[ERROR] MLOps log file {log_path} not found.")

finally:
    # Cleanup background process
    print("\nShutting down FastAPI background server...")
    server_process.terminate()
    server_process.wait()
    print("Server stopped. Demo completed successfully.")
