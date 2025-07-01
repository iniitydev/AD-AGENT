# src/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized application settings loaded from environment variables.
    Uses Pydantic for validation and type enforcement.
    """
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'  # Ignore extra fields from .env file
    )

    # Core Configuration
    ENVIRONMENT: str = Field(default="development", description="Runtime environment.")
    LOG_LEVEL: str = Field(default="INFO", description="Logging verbosity.")

    # Sovereign Data Paths (within the container)
    INPUT_DATA_PATH: str = Field(default="/app/data/dataset.csv", description="Path to input data.")
    MODEL_OUTPUT_PATH: str = Field(default="/app/models/anomaly_model.joblib", description="Path to save trained model.")

    # Model Hyperparameters
    MODEL_CONTAMINATION: float = Field(default=0.1, gt=0, lt=1, description="Expected proportion of anomalies.")
    MODEL_TYPE: str = Field(default="isolation_forest", description="Default model type to be used.")

    # Data Provenance
    MANIFEST_OUTPUT_PATH: str = Field(default="/app/data/manifests/", description="Directory to save data manifests.")
    # Path to a specific data manifest file to be used for verification against INPUT_DATA_PATH
    DATA_MANIFEST_PATH: str = Field(default="/app/data/manifests/default_data_manifest.json", description="Path to the specific data manifest file for verification.")


    # Encryption Settings (from user's Phase 1 encryption spec)
    ENCRYPTION_ENABLED: bool = Field(default=False, description="Whether encryption is active.") # Default to False for safety
    ENCRYPTION_KEY_DERIVATION_ITERATIONS: int = Field(default=100000, description="Number of iterations for PBKDF2 key derivation.")

    # Domain Configuration (anticipating Phase 2)
    DOMAIN: str = Field(default="default", description="Current operational domain for the agent.")
    MODEL_STORE_PATH: str = Field(default="/app/models/store/", description="Path to store versioned models.") # For Phase 2
    EXPERIMENT_LOG_DIR: str = Field(default="/app/logs/experiments/", description="Directory for experiment logs.") # For Phase 2

    # Branding Configuration
    APP_NAME: str = Field(default="Iniity Sovereign AI Agent", description="Application name for branding.")
    COPYRIGHT_HOLDER: str = Field(default="Iniity Inc.", description="Copyright holder for branding.")


# Create a single, importable instance of the settings
settings = Settings()

# To verify loading (optional, can be removed or used in a debug mode)
if __name__ == "__main__":
    print("Settings loaded:")
    print(f"  Environment: {settings.ENVIRONMENT}")
    print(f"  Log Level: {settings.LOG_LEVEL}")
    print(f"  Input Data Path: {settings.INPUT_DATA_PATH}")
    print(f"  Model Output Path: {settings.MODEL_OUTPUT_PATH}")
    print(f"  Model Contamination: {settings.MODEL_CONTAMINATION}")
