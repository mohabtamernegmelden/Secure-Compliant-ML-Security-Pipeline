import os
import json
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder

def main():
    print("Generating dummy ML model and preprocessing assets...")
    
    # Create models directory
    os.makedirs("models", exist_ok=True)
    
    # Define features
    num_cols = ["age", "income", "transaction_amount", "risk_score"]
    cat_cols = ["department", "user_role"]
    
    # Generate dummy training data
    np.random.seed(42)
    n_samples = 200
    
    ages = np.random.randint(18, 90, size=n_samples)
    incomes = np.random.uniform(15000, 300000, size=n_samples)
    amounts = np.random.uniform(5, 25000, size=n_samples)
    scores = np.random.uniform(0.0, 1.0, size=n_samples)
    
    departments = np.random.choice(["finance", "healthcare", "other"], size=n_samples)
    user_roles = np.random.choice(["admin", "analyst", "user"], size=n_samples)
    
    # Target label: 1 if risk score is high or transaction amount is very high relative to income
    y = ((scores > 0.6) | (amounts > incomes * 0.15)).astype(int)
    
    # Preprocessing
    scaler = StandardScaler()
    scaler.fit(np.column_stack((ages, incomes, amounts, scores)))
    
    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    encoder.fit(np.column_stack((departments, user_roles)))
    
    # Transform data
    X_num = scaler.transform(np.column_stack((ages, incomes, amounts, scores)))
    X_cat = encoder.transform(np.column_stack((departments, user_roles)))
    X_train = np.hstack((X_num, X_cat))
    
    # Train dummy model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y)
    
    # Save assets
    joblib.dump(model, "models/best_model.pkl")
    joblib.dump(scaler, "models/scaler.pkl")
    joblib.dump(encoder, "models/encoder.pkl")
    
    feature_config = {
        "numerical_features": num_cols,
        "categorical_features": cat_cols,
        "categories": {
            "department": ["finance", "healthcare", "other"],
            "user_role": ["admin", "analyst", "user"]
        }
    }
    
    with open("models/feature_columns.json", "w") as f:
        json.dump(feature_config, f, indent=4)
        
    print("Assets successfully generated and saved to models/")

if __name__ == "__main__":
    main()
