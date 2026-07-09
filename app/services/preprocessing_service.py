import os
from pathlib import Path
import json
import joblib
import numpy as np
from typing import Dict, Any, List
from app.services.logging_service import app_logger

class PreprocessingService:
    def __init__(self):
        base_dir = Path(__file__).resolve().parents[2]
        models_dir = Path(os.getenv("MODEL_DIR", base_dir / "models"))
        if not models_dir.exists():
            fallback_dir = Path.cwd() / "models"
            if fallback_dir.exists():
                models_dir = fallback_dir
        
        # 1. Load feature columns config dynamically
        config_path = models_dir / "feature_columns.json"
        if not config_path.exists():
            app_logger.error(f"CRITICAL: Feature columns config not found at {config_path}. Preprocessing will be disabled.")
            self.feature_config = None
            self.num_features = []
            self.cat_features = []
            self.scaler = None
            self.encoder = None
            return
            
        with open(config_path, "r") as f:
            self.feature_config = json.load(f)
            
        self.num_features = self.feature_config.get("numerical_features", [])
        self.cat_features = self.feature_config.get("categorical_features", [])
        
        # 2. Load scaler (only if numerical features are present)
        self.scaler = None
        if self.num_features:
            scaler_path = models_dir / "scaler.pkl"
            if not scaler_path.exists():
                app_logger.warning(f"Scaler asset not found at {scaler_path}; using raw numerical values.")
            else:
                self.scaler = joblib.load(scaler_path)
                app_logger.info(f"Loaded scaler and registered {len(self.num_features)} numerical features.")
            
        # 3. Load encoder (only if categorical features are present)
        self.encoder = None
        if self.cat_features:
            encoder_path = models_dir / "encoder.pkl"
            if not encoder_path.exists():
                app_logger.warning(f"Encoder asset not found at {encoder_path}; using raw categorical values.")
            else:
                self.encoder = joblib.load(encoder_path)
                app_logger.info(f"Loaded encoder and registered {len(self.cat_features)} categorical features.")
            
        app_logger.info("Preprocessing service successfully initialized and assets loaded.")

    def preprocess_batch(self, inputs: List[Dict[str, Any]]) -> np.ndarray:
        """
        Preprocesses a list of input dictionaries dynamically based on configuration.
        """
        if self.feature_config is None:
            raise RuntimeError("Preprocessing service is not configured (missing config file).")
            
        processed_parts = []
        
        # Scale numerical features if present
        if self.num_features:
            num_data = []
            for inp in inputs:
                row = [inp[feat] for feat in self.num_features]
                num_data.append(row)
            num_array = np.array(num_data, dtype=float)
            if self.scaler is not None:
                scaled_num = self.scaler.transform(num_array)
                processed_parts.append(scaled_num)
            else:
                processed_parts.append(num_array)
            
        # Encode categorical features if present
        if self.cat_features:
            cat_data = []
            for inp in inputs:
                row = [inp[feat] for feat in self.cat_features]
                cat_data.append(row)
            cat_array = np.array(cat_data)
            if self.encoder is not None:
                encoded_cat = self.encoder.transform(cat_array)
                processed_parts.append(encoded_cat)
            else:
                processed_parts.append(cat_array)
            
        # Stack scaled numerical and/or encoded categorical features
        if not processed_parts:
            # Fallback: if no features are defined, convert the input list values directly
            return np.array([list(inp.values()) for inp in inputs])
            
        processed_data = np.hstack(processed_parts)
        return processed_data

    def preprocess_single(self, input_data: Dict[str, Any]) -> np.ndarray:
        """
        Preprocesses a single input dictionary.
        """
        return self.preprocess_batch([input_data])

# Instantiate service (will load on module import)
preprocessing_service = PreprocessingService()



