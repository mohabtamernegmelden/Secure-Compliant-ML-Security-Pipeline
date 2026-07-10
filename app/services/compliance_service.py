import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.logging_service import app_logger, audit_logger


class ComplianceService:
    def __init__(self, storage_path: Optional[str] = None) -> None:
        self.storage_path = Path(storage_path or os.getenv("COMPLIANCE_STORAGE_PATH", "logs/compliance.json"))
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_store_exists()

    def _ensure_store_exists(self) -> None:
        if not self.storage_path.exists():
            self.storage_path.write_text(json.dumps({"model_changes": [], "audit_events": []}), encoding="utf-8")

    def _load_store(self) -> Dict[str, Any]:
        with self.storage_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_store(self, store: Dict[str, Any]) -> None:
        with self.storage_path.open("w", encoding="utf-8") as handle:
            json.dump(store, handle, indent=2)

    def record_model_change(self, action: str, model_version: str, actor: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "model_version": model_version,
            "actor": actor,
            "details": details or {},
        }
        store = self._load_store()
        store.setdefault("model_changes", []).append(entry)
        self._save_store(store)
        app_logger.info("Model change recorded", extra={"extra_data": entry})
        return entry

    def record_audit_event(self, event: str, user: str, status: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "user": user,
            "status": status,
            "details": details or {},
        }
        store = self._load_store()
        store.setdefault("audit_events", []).append(entry)
        self._save_store(store)
        audit_logger.info("Compliance audit event recorded", extra={"extra_data": entry})
        return entry

    def get_model_change_history(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        return store.get("model_changes", [])

    def get_audit_event_history(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        return store.get("audit_events", [])[-10:]

    def get_pipeline_status(self) -> Dict[str, Any]:
        return {
            "audit_logs_enabled": True,
            "model_change_tracking": True,
            "recent_model_changes": self.get_model_change_history(),
            "recent_audit_events": self.get_audit_event_history(),
        }


compliance_service = ComplianceService()
