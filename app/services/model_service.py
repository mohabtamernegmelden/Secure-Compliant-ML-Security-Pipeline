import os
from pathlib import Path
import joblib
import numpy as np
from typing import Any, Tuple
from app.services.logging_service import app_logger

class ModelService:
    def __init__(self):
        base_dir = Path(__file__).resolve().parents[2]
        models_dir = Path(os.getenv("MODEL_DIR", base_dir / "models"))
        if not models_dir.exists():
            fallback_dir = Path.cwd() / "models"
            if fallback_dir.exists():
                models_dir = fallback_dir
        model_path = models_dir / "best_model.pkl"
        
        if not model_path.exists():
            app_logger.error(f"CRITICAL: Model file not found at {model_path}. Prediction endpoints will be disabled.")
            self.model = None
            self.model_version = "UNKNOWN"
            return
            
        app_logger.info(f"Loading ML model from {model_path}...")
        self.model = joblib.load(model_path)
        self.model_version = "1.0.0"
        app_logger.info(f"Model version {self.model_version} loaded successfully.")

    def predict(self, features: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run inference on preprocessed features.
        Returns:
            Tuple of (predictions, probabilities)
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded.")
            
        predictions = np.asarray(self.model.predict(features))
        
        # Check if the model supports predict_proba (most classifiers do)
        if hasattr(self.model, "predict_proba"):
            probabilities = np.asarray(self.model.predict_proba(features))
            if probabilities.ndim == 1:
                probabilities = probabilities.reshape(-1, 1)
            if probabilities.shape[1] == 1:
                positive_probabilities = probabilities[:, 0]
                probabilities = np.column_stack((1 - positive_probabilities, positive_probabilities))
            else:
                positive_probabilities = probabilities[:, -1]
                probabilities = np.column_stack((1 - positive_probabilities, positive_probabilities))
        else:
            # Handle regression or models without probabilities gracefully
            probabilities = np.column_stack((1 - predictions.astype(float), predictions.astype(float)))
            
        return predictions, probabilities

# Instantiate service (will load on module import)
model_service = ModelService()



