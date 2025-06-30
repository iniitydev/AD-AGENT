# src/agent/detection.py
from pathlib import Path
import pandas as pd
import joblib
import datetime # <--- Import datetime
# from pyod.models.iforest import IForest # Example from PyOD - replaced by KNN in user spec
from pyod.models.knn import KNN # As per user's Phase 1 spec
from typing import Optional # Import Optional for type hinting

from src.config import settings
from src.logger import get_logger
from src.agent.preprocessing import preprocess_pipeline # Assuming this is still the main preprocessing entry
from src.agent.data_manifest import create_data_manifest, save_manifest # Added save_manifest

logger = get_logger(__name__)

# --- Model Training ---
# Updated to accept path overrides
def train_model(input_path_override: Optional[str] = None,
                output_path_override: Optional[str] = None,
                manifest_dir_override: Optional[str] = None):
    """Train model from CSV and save to disk."""
    input_p = Path(input_path_override or settings.INPUT_DATA_PATH)
    output_p = Path(output_path_override or settings.MODEL_OUTPUT_PATH)
    manifest_output_dir_p = Path(manifest_dir_override or settings.MANIFEST_OUTPUT_PATH)

    logger.info(f"Starting model training. Input: {input_p}, Model Output: {output_p}, Manifest Dir: {manifest_output_dir_p}")

    if not input_p.exists():
        logger.error(f"Input data file not found: {input_p}")
        raise FileNotFoundError(f"Input data file not found: {input_p}")

    logger.info(f"Preprocessing data from {input_p}...")
    processed_data = preprocess_pipeline(str(input_p)) # Ensure input_p is string

    if processed_data.empty:
        logger.error("Preprocessing returned empty data. Cannot train model.")
        raise ValueError("Preprocessing returned empty data. Cannot train model.")

    # Data provenance tracking (as per user's Phase 1 spec for detection.py)
    # Note: User's snippet for create_data_manifest had `input_p` as Path, `output_dir` as Path
    # and `additional_metadata` with `features`: list(numeric_data.columns).
    # Since numeric_data is now `processed_data`, I'll use its columns.
    # Also, manifest_entry was just printed, let's save it.
    manifest_output_dir_p.mkdir(parents=True, exist_ok=True) # Ensure manifest dir exists

    # The manifest file name could be based on input data or timestamp
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_file_name = f"manifest_{input_p.stem}_{timestamp_str}.json"
    full_manifest_path = manifest_output_dir_p / manifest_file_name

    manifest_data = create_data_manifest(
        data_path=str(input_p), # Original input path
        model_path=str(output_p), # Expected model output path
        metadata={ # Renamed from additional_metadata for clarity with create_data_manifest signature
            "rows_processed": len(processed_data), # Number of rows after preprocessing
            "features_processed": list(processed_data.columns), # Use columns from processed_data
            "model_type": settings.MODEL_TYPE, # From config
            "model_contamination": settings.MODEL_CONTAMINATION, # From config
            "source_info": "Training dataset" # Added source_info
        }
    )
    save_manifest(manifest_data, str(full_manifest_path))
    logger.info(f"📝 Created and saved data manifest entry: {full_manifest_path}")


    # Model training (as per user's Phase 1 spec for detection.py)
    logger.info(f"Training model ({settings.MODEL_TYPE}) with contamination: {settings.MODEL_CONTAMINATION}...")
    # model = KNN(contamination=settings.MODEL_CONTAMINATION) # PyOD KNN
    # Dynamically select model based on MODEL_TYPE if we want to support more
    if settings.MODEL_TYPE.lower() == 'knn':
        model = KNN(contamination=settings.MODEL_CONTAMINATION)
    elif settings.MODEL_TYPE.lower() == 'isolation_forest':
        from pyod.models.iforest import IForest # Keep IForest as an option
        model = IForest(contamination=settings.MODEL_CONTAMINATION, behaviour='new', random_state=42)
    else:
        logger.error(f"Unsupported MODEL_TYPE: {settings.MODEL_TYPE}. Defaulting to KNN.")
        model = KNN(contamination=settings.MODEL_CONTAMINATION)

    model.fit(processed_data)

    # Save model
    output_p.parent.mkdir(parents=True, exist_ok=True) # Ensure model dir exists
    joblib.dump(model, output_p)
    logger.info(f"✅ Model saved to {output_p}")
    return model


# --- Prediction ---
# Updated to accept model_path_override
def predict_data(data_path: str, model_path_override: Optional[str] = None):
    """
    Loads a trained model and runs predictions on new data.
    """
    model_p = Path(model_path_override or settings.MODEL_OUTPUT_PATH)
    logger.info(f"Starting prediction using model from: {model_p}")
    logger.info(f"Predicting on data from: {data_path}")

    if not model_p.exists():
        logger.error(f"Model file not found: {model_p}")
        raise FileNotFoundError(f"Model file not found: {model_p}")

    try:
        # 1. Load the trained model
        model = joblib.load(model_path)
        logger.info("Model loaded successfully.")

        # 2. Load and preprocess new data
        logger.info("Preprocessing new data...")
        new_data_processed = preprocess_pipeline(data_path) # Use the imported pipeline

        if new_data_processed.empty:
            logger.error("Preprocessing returned empty data for prediction. Cannot make predictions.")
            raise ValueError("Preprocessing returned empty data for prediction.")

        # 3. Make predictions
        # PyOD models: predict() returns binary labels (0 normal, 1 anomaly)
        # decision_function() returns raw anomaly scores.
        predictions_binary = model.predict(new_data_processed) # 0 or 1
        # anomaly_scores = model.decision_function(new_data_processed)

        logger.info("Prediction completed.")

        # Return a structured result
        # Create a DataFrame from the processed data's index to align results if needed
        results_df = pd.DataFrame(index=new_data_processed.index)
        results_df['is_anomaly'] = predictions_binary
        # results_df['anomaly_score'] = anomaly_scores
        # results_df['original_data_path'] = data_path # Could be useful context

        return results_df.to_dict(orient='records')

    except FileNotFoundError: # Handles data_path not found if preprocess_pipeline raises it
        logger.error(f"Data file for prediction not found: {data_path}")
        raise
    except Exception as e:
        logger.error(f"Error during prediction: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    # Example usage for testing this module directly
    from pathlib import Path
    import datetime # For timestamp in manifest name

    project_root_for_test = Path(__file__).resolve().parent.parent.parent

    # Override settings for local testing if .env isn't configured for it
    settings.INPUT_DATA_PATH = str(project_root_for_test / "data" / "dataset.csv")
    settings.MODEL_OUTPUT_PATH = str(project_root_for_test / "models" / "anomaly_model_test.joblib")
    settings.MANIFEST_OUTPUT_PATH = str(project_root_for_test / "data" / "manifests_test")
    settings.MODEL_TYPE = "knn" # Or "isolation_forest"
    settings.LOG_LEVEL = "DEBUG" # More verbose for testing

    # Re-initialize logger if LOG_LEVEL changed (simple re-init for testing)
    logger.setLevel(settings.LOG_LEVEL.upper())
    for handler in logger.handlers: # Propagate to handlers if any exist
        handler.setLevel(settings.LOG_LEVEL.upper())
    logger.info(f"Logger level set to {settings.LOG_LEVEL} for testing.")


    sample_data_file = Path(settings.INPUT_DATA_PATH)
    sample_data_file.parent.mkdir(parents=True, exist_ok=True)
    Path(settings.MODEL_OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.MANIFEST_OUTPUT_PATH).mkdir(parents=True, exist_ok=True)

    if not sample_data_file.exists() or sample_data_file.stat().st_size == 0:
        pd.DataFrame({
            'feature1': [1, 1.1, 1.2, 0.9, 10, 1.3, 0.8, 10.5, 1.1, 1.0] * 10,
            'feature2': [2, 2.2, 2.1, 1.9, 20, 2.3, 1.8, 20.5, 2.1, 2.0] * 10,
            'id_col': range(100)
        }).to_csv(sample_data_file, index=False)
        logger.info(f"Created dummy data at {sample_data_file}")

    logger.info("--- Testing train_model() ---")
    try:
        trained_model = train_model()
        logger.info(f"Trained model type: {type(trained_model)}")
    except Exception as e:
        logger.error(f"Error testing train_model: {e}", exc_info=True)

    logger.info("\n--- Testing predict_data() ---")
    if Path(settings.MODEL_OUTPUT_PATH).exists():
        try:
            predictions = predict_data(settings.INPUT_DATA_PATH)
            if predictions:
                logger.info(f"Predictions (first 5 of {len(predictions)}): {predictions[:5]}")
            else:
                logger.warning("Prediction returned no results.")
        except Exception as e:
            logger.error(f"Error testing predict_data: {e}", exc_info=True)
    else:
        logger.warning(f"Skipping predict_data test as model file {settings.MODEL_OUTPUT_PATH} was not created.")

    # Clean up test model and manifest if needed, or leave for inspection
    # logger.info(f"Test model at: {settings.MODEL_OUTPUT_PATH}")
    # logger.info(f"Test manifests at: {settings.MANIFEST_OUTPUT_PATH}")
