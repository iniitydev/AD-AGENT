# src/agent/data_manifest.py
from src.logger import get_logger
import hashlib
import json
from datetime import datetime
from pathlib import Path

logger = get_logger(__name__)

# This is a placeholder implementation.
# The actual implementation would depend on the specifics of how data provenance
# and manifest generation were handled in the original project or desired features.

def generate_file_hash(filepath: str, algorithm: str = "sha256") -> str:
    """Generates a hash for a given file."""
    h = hashlib.new(algorithm)
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        logger.error(f"File not found for hashing: {filepath}")
        return "FILE_NOT_FOUND"
    except Exception as e:
        logger.error(f"Error hashing file {filepath}: {e}", exc_info=True)
        return "HASHING_ERROR"

def create_data_manifest(data_path: str, model_path: str = None, metadata: dict = None) -> dict:
    """
    Creates a basic data manifest.
    This is a simplified example. A real manifest might include:
    - More detailed metadata about the data source.
    - Information about preprocessing steps applied.
    - Versioning information for data and models.
    - Cryptographic signatures for integrity.
    """
    logger.info(f"Creating data manifest for data: {data_path}")
    manifest = {
        "manifest_version": "1.0.0",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "data_input": {
            "path": data_path,
            "hash_sha256": generate_file_hash(data_path),
            "size_bytes": Path(data_path).stat().st_size if Path(data_path).exists() else -1,
        },
        "processing_details": {
            "agent_version": "2.5.0", # Should come from a central place
            # Add details about preprocessing steps, parameters, etc.
            "preprocessing_steps": ["loaded_data", "cleaned_data", "selected_features", "scaled_features"]
        }
    }

    if model_path and Path(model_path).exists():
        manifest["model_output"] = {
            "path": str(model_path), # Ensure string for JSON
            "hash_sha256": generate_file_hash(str(model_path)),
            "size_bytes": Path(model_path).stat().st_size,
        }

    if metadata:
        manifest["custom_metadata"] = metadata

    # Add encryption metadata if available (as per user's Phase 1 spec)
    from src.config import settings as current_settings # renamed to avoid conflict with function arg
    if current_settings.ENCRYPTION_ENABLED: # Check if ENCRYPTION_ENABLED is a valid attribute
        manifest["encryption_metadata"] = { # Changed key name for clarity
            "algorithm": "AES-GCM", # Placeholder, actual could be more dynamic
            "key_derivation": "PBKDF2HMAC-SHA256", # Placeholder
            "iterations": current_settings.ENCRYPTION_KEY_DERIVATION_ITERATIONS
        }

    logger.info(f"Data manifest created: {manifest}")
    return manifest

def save_manifest(manifest_data: dict, output_path: str):
    """Saves the manifest data to a JSON file, ensuring the directory exists."""
    manifest_file_path = Path(output_path)
    manifest_file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_path, 'w') as f:
            json.dump(manifest_data, f, indent=4)
        logger.info(f"Manifest saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save manifest to {output_path}: {e}", exc_info=True)

if __name__ == "__main__":
    # Example usage
    from src.config import settings # For INPUT_DATA_PATH, MODEL_OUTPUT_PATH

    # Create dummy files for testing manifest generation
    dummy_data_file = Path(settings.INPUT_DATA_PATH)
    dummy_model_file = Path(settings.MODEL_OUTPUT_PATH) # Assuming a model was trained

    dummy_data_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_model_file.parent.mkdir(parents=True, exist_ok=True)

    if not dummy_data_file.exists():
        with open(dummy_data_file, "w") as f:
            f.write("dummy,data\n1,2\n3,4")
        logger.info(f"Created dummy data file: {dummy_data_file}")

    if not dummy_model_file.exists():
        # Simulate a model file
        import joblib
        dummy_model = {"model_type": "dummy_sklearn_model"}
        joblib.dump(dummy_model, dummy_model_file)
        logger.info(f"Created dummy model file: {dummy_model_file}")

    logger.info("--- Testing Data Manifest Generation ---")
    manifest = create_data_manifest(
        data_path=str(dummy_data_file),
        model_path=str(dummy_model_file),
        metadata={"source_system": "test_system", "run_id": "run_123"}
    )

    manifest_output_path = dummy_data_file.parent / "test_data_manifest.json"
    save_manifest(manifest, str(manifest_output_path))
    logger.info(f"Test manifest generated at: {manifest_output_path}")

    # Clean up dummy files
    # if dummy_data_file.exists():
    #     dummy_data_file.unlink()
    # if dummy_model_file.exists():
    #     dummy_model_file.unlink()
    # if manifest_output_path.exists():
    #     manifest_output_path.unlink()
    # logger.info("Cleaned up dummy files for manifest test.")


def verify_data_integrity(data_file_path: str, manifest_file_path: str) -> dict:
    """
    Verifies the integrity of a data file against a specific manifest entry.
    This is a simplified example. A more robust version would:
    - Find the specific entry for data_file_path within a larger manifest file if needed.
    - Handle cases where the manifest might contain multiple entries.
    """
    logger.info(f"Verifying data integrity for {data_file_path} using manifest {manifest_file_path}")

    p_data_file_path = Path(data_file_path)
    p_manifest_file_path = Path(manifest_file_path)

    if not p_data_file_path.exists():
        logger.error(f"Data file not found: {p_data_file_path}")
        return {"status": "error", "reason": "Data file not found", "file": str(p_data_file_path)}

    if not p_manifest_file_path.exists():
        logger.error(f"Manifest file not found: {p_manifest_file_path}")
        return {"status": "error", "reason": "Manifest file not found", "file": str(p_manifest_file_path)}

    try:
        with open(p_manifest_file_path, "r") as f:
            manifest_data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Could not read or parse manifest file {p_manifest_file_path}: {e}", exc_info=True)
        return {"status": "error", "reason": f"Cannot read/parse manifest: {e}", "file": str(p_manifest_file_path)}

    # Assuming the manifest file directly corresponds to the data file
    # or that the manifest structure is simple (e.g., created by create_data_manifest for a single data file)

    expected_hash = manifest_data.get("data_input", {}).get("hash_sha256")
    manifested_path = manifest_data.get("data_input", {}).get("path")

    if not expected_hash:
        logger.error(f"No hash found in manifest {p_manifest_file_path} for data_input.")
        return {"status": "error", "reason": "No hash in manifest for data_input", "manifest": str(p_manifest_file_path)}

    # Optional: Check if the path in manifest matches the provided data_file_path
    # This depends on whether manifest_file_path is a generic manifest or specific to data_file_path
    if manifested_path and Path(manifested_path).name != p_data_file_path.name: # Simple name check
        logger.warning(f"Manifest path {manifested_path} differs from data file path {data_file_path}. Proceeding with hash check.")
        # This could be an error depending on strictness.

    current_hash = generate_file_hash(str(p_data_file_path))

    if current_hash == "FILE_NOT_FOUND" or current_hash == "HASHING_ERROR":
        return {"status": "error", "reason": f"Could not hash data file {p_data_file_path}", "file": str(p_data_file_path)}

    if current_hash == expected_hash:
        logger.info(f"Data integrity VERIFIED for {p_data_file_path}")
        return {"status": "verified", "file": str(p_data_file_path), "hash": current_hash}
    else:
        logger.warning(f"Data integrity TAMPERED for {p_data_file_path}. Expected hash: {expected_hash}, current hash: {current_hash}")
        return {"status": "tampered", "file": str(p_data_file_path), "expected_hash": expected_hash, "current_hash": current_hash}
