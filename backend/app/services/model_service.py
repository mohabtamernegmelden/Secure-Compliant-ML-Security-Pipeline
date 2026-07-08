import os
import joblib
import numpy as np
from typing import Any, Tuple
from app.services.logging_service import app_logger

class ModelService:
    def __init__(self):
        models_dir = "models"
        model_path = os.path.join(models_dir, "best_model.pkl")
        
        if not os.path.exists(model_path):
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
            
        predictions = self.model.predict(features)
        
        # Check if the model supports predict_proba (most classifiers do)
        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(features)
        else:
            # Handle regression or models without probabilities gracefully
            probabilities = np.column_stack((1 - predictions, predictions))
            
        return predictions, probabilities

# Instantiate service (will load on module import)
model_service = ModelService()



