# src/agent/preprocessing.py
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler # Example scalers
# from sklearn.impute import SimpleImputer # Example imputer

from src.config import settings # If needed for specific preprocessing params
from src.logger import get_logger

logger = get_logger(__name__)

def load_data(data_path: str) -> pd.DataFrame:
    """
    Loads data from the specified path.
    Currently supports CSV. Extend for other formats if needed.
    """
    logger.info(f"Loading data from: {data_path}")
    try:
        # TODO: Add support for other file types based on extension (e.g., .npy, .parquet)
        if data_path.endswith('.csv'):
            df = pd.read_csv(data_path)
        elif data_path.endswith('.npy'):
            # Assuming npy is just the features, may need labels separately
            # This part needs to align with how .npy data was used in the original project
            logger.warning("Loading .npy files needs specific handling. Assuming it's a feature array.")
            data = pd.np.load(data_path) # Allow pickle if necessary from original project
            df = pd.DataFrame(data)
        else:
            logger.error(f"Unsupported file format for data_path: {data_path}")
            raise ValueError(f"Unsupported file format: {data_path}. Please use .csv or .npy (with adjustments).")

        logger.info(f"Data loaded successfully. Shape: {df.shape}")
        return df
    except FileNotFoundError:
        logger.error(f"Data file not found at {data_path}")
        raise
    except pd.errors.EmptyDataError:
        logger.error(f"Data file at {data_path} is empty.")
        raise
    except Exception as e:
        logger.error(f"Error loading data from {data_path}: {e}", exc_info=True)
        raise

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Performs basic data cleaning.
    - Handles missing values (example: mean imputation for numeric).
    - Removes duplicate rows.
    """
    logger.info(f"Starting data cleaning. Initial shape: {df.shape}")

    # Handle missing values (example: fill NaNs in numeric columns with mean)
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        if df[col].isnull().any():
            mean_val = df[col].mean()
            df[col].fillna(mean_val, inplace=True)
            logger.debug(f"Filled NaNs in column '{col}' with mean value: {mean_val:.2f}")

    # Handle missing values in non-numeric columns (example: fill with 'Unknown' or mode)
    non_numeric_cols = df.select_dtypes(exclude=['number']).columns
    for col in non_numeric_cols:
        if df[col].isnull().any():
            mode_val = df[col].mode()[0] if not df[col].mode().empty else 'Unknown'
            df[col].fillna(mode_val, inplace=True)
            logger.debug(f"Filled NaNs in column '{col}' with mode value: {mode_val}")

    # Remove duplicate rows
    initial_rows = len(df)
    df.drop_duplicates(inplace=True)
    if len(df) < initial_rows:
        logger.info(f"Removed {initial_rows - len(df)} duplicate rows.")

    logger.info(f"Data cleaning finished. Shape after cleaning: {df.shape}")
    return df

def select_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Selects features for model training/prediction.
    Currently, it only selects numeric features.
    This should be adapted based on the old project's feature handling.
    """
    logger.info("Selecting features for the model.")

    # For many anomaly detection models, only numeric features are used.
    numeric_df = df.select_dtypes(include=['number'])

    if numeric_df.empty:
        logger.error("No numeric columns found after cleaning. Cannot proceed with model training/prediction.")
        raise ValueError("No numeric data to process. Please ensure your data has numeric features.")

    # Potentially drop ID columns or columns with no variance if they exist
    # Example:
    # cols_to_drop = [col for col in numeric_df.columns if numeric_df[col].nunique() == 1]
    # if cols_to_drop:
    #     logger.info(f"Dropping columns with no variance: {cols_to_drop}")
    #     numeric_df = numeric_df.drop(columns=cols_to_drop)

    logger.info(f"Selected {len(numeric_df.columns)} numeric features: {list(numeric_df.columns)}")
    return numeric_df

def scale_features(df: pd.DataFrame, scaler_type: str = "standard") -> pd.DataFrame:
    """
    Scales numeric features.
    """
    logger.info(f"Scaling features using {scaler_type} scaler.")
    if df.empty:
        logger.warning("Dataframe for scaling is empty. Returning as is.")
        return df

    if scaler_type == "standard":
        scaler = StandardScaler()
    elif scaler_type == "minmax":
        scaler = MinMaxScaler()
    else:
        logger.warning(f"Unknown scaler type: {scaler_type}. Defaulting to StandardScaler.")
        scaler = StandardScaler()

    scaled_data = scaler.fit_transform(df)
    scaled_df = pd.DataFrame(scaled_data, columns=df.columns, index=df.index)

    logger.info("Feature scaling complete.")
    return scaled_df


def preprocess_pipeline(data_path: str, scaler_type: str = "standard") -> pd.DataFrame:
    """
    Full preprocessing pipeline: Load, Clean, Select Features, Scale.
    This function will be called by detection.py.
    """
    logger.info(f"--- Starting preprocessing pipeline for: {data_path} ---")

    # 1. Load Data
    raw_df = load_data(data_path)

    # 2. Clean Data
    cleaned_df = clean_data(raw_df.copy()) # Use .copy() to avoid SettingWithCopyWarning on slices

    # 3. Select Features (currently only numeric)
    #    This might happen before or after scaling depending on strategy
    #    For now, selecting numeric features before scaling.
    features_df = select_features(cleaned_df)

    if features_df.empty:
        logger.error("No features selected. Aborting preprocessing.")
        raise ValueError("No features were selected from the data.")

    # 4. Scale Features
    #    Only scale if there's data.
    if not features_df.empty:
        scaled_features_df = scale_features(features_df, scaler_type=scaler_type)
    else:
        logger.warning("Skipping scaling as no features were selected or data is empty.")
        scaled_features_df = features_df # or pd.DataFrame()

    logger.info(f"--- Preprocessing pipeline finished. Final data shape: {scaled_features_df.shape} ---")
    return scaled_features_df


if __name__ == '__main__':
    # Example usage for testing this module directly
    # Create a dummy CSV for testing
    dummy_data_path = "dummy_preprocess_test.csv"
    pd.DataFrame({
        'id': [1, 2, 3, 4, 5, 6],
        'numeric_feature1': [10, 12, None, 15, 10, 12], # Added None for missing value test
        'numeric_feature2': [0.5, 0.3, 0.8, 0.5, 0.5, 0.3],
        'categorical_feature': ['A', 'B', 'A', 'C', None, 'B'], # Added None
        'text_data': ['some text', 'more text', 'example', 'text', 'another', 'more text']
    }).to_csv(dummy_data_path, index=False)

    logger.info(f"--- Testing preprocessing_pipeline with {dummy_data_path} ---")
    try:
        processed_data = preprocess_pipeline(dummy_data_path)
        logger.info("Processed Data Head:")
        logger.info(processed_data.head())
        logger.info(f"Processed Data Shape: {processed_data.shape}")

        # Verify no NaNs in processed data (numeric parts)
        if processed_data.isnull().sum().sum() == 0:
            logger.info("No NaNs found in the processed numeric data. Good.")
        else:
            logger.error("NaNs found in processed data! Check cleaning/imputation.")
            logger.error(processed_data.isnull().sum())

    except Exception as e:
        logger.error(f"Error during pipeline test: {e}", exc_info=True)
    finally:
        # Clean up dummy file
        import os
        if os.path.exists(dummy_data_path):
            os.remove(dummy_data_path)
            logger.info(f"Cleaned up {dummy_data_path}")
