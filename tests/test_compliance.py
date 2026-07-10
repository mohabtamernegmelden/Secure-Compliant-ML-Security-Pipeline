import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.compliance_service import compliance_service

client = TestClient(app)


def test_compliance_endpoint_reports_pipeline_status():
    response = client.get("/compliance")
    assert response.status_code == 200
    data = response.json()
    assert data["compliance_pipeline"]["audit_logs_enabled"] is True
    assert data["compliance_pipeline"]["model_change_tracking"] is True
    assert "recent_model_changes" in data["compliance_pipeline"]
    assert "recent_audit_events" in data["compliance_pipeline"]


def test_model_change_tracking_records_a_change_event():
    before_count = len(compliance_service.get_model_change_history())
    compliance_service.record_model_change(
        "load",
        "1.0.0",
        "test",
        {"status": "ok"},
    )
    after_count = len(compliance_service.get_model_change_history())
    assert after_count >= before_count + 1
