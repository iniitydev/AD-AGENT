# src/main.py
import click
import uvicorn
from fastapi import FastAPI
from pathlib import Path
import json
import sys

from src.config import settings as global_settings # For initial log
from src.config import Settings # For reloading in commands

try:
    from src.agent.detection import train_model as run_training_process
    from src.agent.detection import predict_data
except ImportError:
    import logging
    logger_placeholder = logging.getLogger(__name__)
    def run_training_process(input_path_override=None, output_path_override=None, manifest_dir_override=None):
        logger_placeholder.warning("run_training_process function is not yet implemented.")
        click.echo("Placeholder: Model training would occur here.")
        return True
    def predict_data(data_path: str, model_path_override=None):
        logger_placeholder.warning(f"predict_data function is not yet implemented for data_path: {data_path}.")
        click.echo(f"Placeholder: Prediction would occur here for {data_path}")
        return {"predictions": "dummy_predictions"}

from src.logger import get_logger

# Imports for the verify command
from scripts.verify_integrity import verify_integrity as perform_code_integrity_check_func
from src.agent.data_manifest import verify_data_integrity as perform_data_file_manifest_check_func

logger = get_logger(__name__)

class VerificationError(click.ClickException):
    exit_code = 1
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}

    def format_message(self):
        msg = f"❌ {self.message}"
        if self.details:
            try:
                details_json = json.dumps(self.details, indent=2)
                msg += f"\nDetails:\n{details_json}"
            except TypeError:
                msg += f"\nDetails (raw): {str(self.details)}"
        return msg

def verify_integrity_at_startup():
    from scripts.verify_integrity import verify_integrity as full_script_verify
    try:
        logger.info("Performing startup integrity check...")
        if not full_script_verify(project_root="."):
            logger.critical("Startup integrity check FAILED. Application will not start. See script output above for details.")
            sys.exit(1)
        logger.info("Startup integrity check PASSED.")
    except Exception as e:
        logger.critical(f"Startup integrity check FAILED with exception: {e}. Application will not start.")
        sys.exit(1)

verify_integrity_at_startup()


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option("2.5.0", prog_name="sovereign-ad-agent", message="%(prog)s, version %(version)s, developed by iniity.com")
def cli():
    logger.info(f"Sovereign AD Agent CLI invoked. Environment: {global_settings.ENVIRONMENT}, Log Level: {global_settings.LOG_LEVEL}")
    pass

@cli.command()
@click.option('--input-data-path', default=None, type=click.Path(), help=f'Path to input data.')
@click.option('--model-output-path', default=None, type=click.Path(), help=f'Path to save model.')
@click.option('--manifest-output-path', default=None, type=click.Path(), help=f'Directory to save data manifest.')
def train(input_data_path, model_output_path, manifest_output_path):
    settings = Settings()
    final_input_data_path = Path(input_data_path or settings.INPUT_DATA_PATH)
    final_model_output_path = Path(model_output_path or settings.MODEL_OUTPUT_PATH)
    final_manifest_output_path = Path(manifest_output_path or settings.MANIFEST_OUTPUT_PATH)

    logger.info(f"Starting model training process:")
    logger.info(f"  Input data: {final_input_data_path}")
    logger.info(f"  Model output: {final_model_output_path}")
    logger.info(f"  Manifest output dir: {final_manifest_output_path}")
    try:
        run_training_process(input_path_override=str(final_input_data_path),
                             output_path_override=str(final_model_output_path),
                             manifest_dir_override=str(final_manifest_output_path))
        logger.info("Model training complete.")
        click.echo(click.style("✅ Model training finished successfully.", fg="green"))
    except Exception as e:
        logger.error(f"Model training failed: {e}", exc_info=True)
        click.echo(click.style(f"❌ Model training failed: {e}", fg="red"), err=True)

@cli.command()
@click.option('--input-file', default=None, type=click.Path(exists=True, dir_okay=False, readable=True), help='Path to new data file for prediction.')
@click.option('--model-input-path', default=None, type=click.Path(exists=True, dir_okay=False, readable=True), help=f'Path to load model from.')
def predict(input_file, model_input_path):
    settings = Settings()
    final_input_file = Path(input_file or settings.INPUT_DATA_PATH)
    final_model_input_path = Path(model_input_path or settings.MODEL_OUTPUT_PATH)

    logger.info(f"Running prediction on data: {final_input_file} using model: {final_model_input_path}")
    try:
        predictions = predict_data(str(final_input_file), model_path_override=str(final_model_input_path))
        click.echo(f"Predictions for {final_input_file}:")
        click.echo(predictions)
        logger.info("Prediction complete.")
        click.echo(click.style("✅ Prediction finished successfully.", fg="green"))
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        click.echo(click.style(f"❌ Prediction failed: {e}", fg="red"), err=True)

@cli.command()
def serve():
    settings = Settings()
    logger.info(f"Attempting to start API server on http://0.0.0.0:8000")
    app = FastAPI(title="Sovereign Anomaly Detection Agent API", version="2.5.0")
    @app.get("/")
    def read_root():
        return {"message": "Sovereign Anomaly Detection Agent is running."}
    @app.get("/health")
    def health_check():
        return {"status": "ok"}
    click.echo(click.style(f"🚀 API server starting. Docs at http://localhost:8000/docs", fg="cyan"))
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=settings.LOG_LEVEL.lower())

@cli.command(name="config")
def config_cmd():
    settings = Settings()
    click.echo(click.style("--- Current Configuration ---", fg="cyan"))
    for key, val in settings.model_dump().items():
        click.echo(f"{key.upper()}: {val}")
    click.echo(click.style("-----------------------------", fg="cyan"))

@cli.command()
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Encryption password.')
@click.option('--input-file', required=True, type=click.Path(exists=True, dir_okay=False, readable=True), help='File to encrypt.')
@click.option('--output-file', default=None, type=click.Path(dir_okay=False, writable=True), help='Output file path (default: input_file.enc).')
def encrypt(password, input_file, output_file):
    from src.agent.encryption import encrypt_file
    logger.info(f"CLI encrypt command invoked for input: {input_file}")
    try:
        encrypted_path, salt = encrypt_file(input_file, password, output_file)
        click.echo(click.style(f"✅ File encrypted successfully.", fg="green"))
        click.echo(f"   Encrypted file: {encrypted_path}")
        click.echo(click.style(f"🔑 Key derivation salt (hex): {salt.hex()}", fg="yellow"))
    except Exception as e:
        raise VerificationError(f"File encryption failed: {str(e)}", details={"input": input_file, "error": str(e)})

@cli.command()
@click.option('--password', prompt=True, hide_input=True, help='Decryption password.')
@click.option('--input-file', required=True, type=click.Path(exists=True, dir_okay=False, readable=True), help='File to decrypt.')
@click.option('--output-file', default=None, type=click.Path(dir_okay=False, writable=True), help='Output file path.')
def decrypt(password, input_file, output_file):
    from src.agent.encryption import decrypt_file
    logger.info(f"CLI decrypt command invoked for input: {input_file}")
    try:
        decrypted_path = decrypt_file(input_file, password, output_file)
        click.echo(click.style(f"✅ File decrypted successfully.", fg="green"))
        click.echo(f"   Decrypted file:  {decrypted_path}")
    except Exception as e:
        raise VerificationError(f"File decryption failed: {str(e)}", details={"input": input_file, "error": str(e)})

@cli.command()
def verify():
    settings = Settings() # Reload settings for this command
    errors_found_list = []
    code_integrity_passed = False
    data_integrity_passed = False # For the specific DATA_MANIFEST_PATH check
    project_root_for_code_verify = Path(__file__).resolve().parent.parent

    # 1. Code Integrity Verification
    click.echo(click.style("🔐 Verifying code integrity (via script)...", fg="cyan", bold=True))
    try:
        if perform_code_integrity_check_func(project_root=str(project_root_for_code_verify)):
            click.echo(click.style("✅ Code integrity script check passed (called by CLI).", fg="green")) # Explicit message
            code_integrity_passed = True
        else:
            errors_found_list.append({"category": "code_integrity",
                                   "message": "Overall code integrity script reported issues. See script output above."})
    except Exception as e:
        logger.error(f"Error during code integrity script execution: {e}", exc_info=True)
        errors_found_list.append({"category": "code_integrity_execution",
                               "message": f"Script execution error: {str(e)}"})

    # 2. Data Provenance Verification (for specific data file against its specific manifest)
    click.echo(click.style("\n📊 Verifying specific data manifest...", fg="cyan", bold=True))
    try:
        data_path = Path(settings.INPUT_DATA_PATH)
        manifest_file_to_check = Path(settings.DATA_MANIFEST_PATH)

        if not data_path.exists():
            msg = f"Data file for specific manifest check not found: {data_path}"
            dtls = {"expected_data_path": str(data_path)}
            logger.error(f"{msg} - Details: {json.dumps(dtls)}")
            errors_found_list.append({"category": "data_file_missing_for_specific_manifest",
                                   "message": msg, "details": dtls})
        elif not manifest_file_to_check.exists():
            msg = f"Specific data manifest file not found: {manifest_file_to_check}"
            dtls = {"expected_manifest_path": str(manifest_file_to_check),
                    "data_file_to_be_checked": str(data_path)}
            logger.error(f"{msg} - Details: {json.dumps(dtls)}")
            errors_found_list.append({"category": "specific_data_manifest_missing",
                                   "message": msg, "details": dtls})
        else:
            click.echo(f"   Using input data for specific check: {data_path}")
            click.echo(f"   Using specific manifest file: {manifest_file_to_check}")
            result = perform_data_file_manifest_check_func(str(data_path), str(manifest_file_to_check))
            click.echo(json.dumps(result, indent=2))
            if result.get("status") == "verified":
                data_integrity_passed = True
            elif result.get("status") == "tampered":
                errors_found_list.append({"category": "specific_data_manifest_tampered",
                                       "message": "Tampering detected for specific data manifest.",
                                       "details": result})
            else:
                errors_found_list.append({"category": "specific_data_manifest_error",
                                       "message": f"Integrity check issue for specific data manifest: {result.get('reason', 'Unknown')}",
                                       "details": result})
    except Exception as e:
        logger.error(f"Error during specific data manifest verification: {e}", exc_info=True)
        errors_found_list.append({"category": "specific_data_manifest_exception",
                               "message": f"Execution error: {str(e)}"})

    if data_integrity_passed:
        click.echo(click.style("✅ Specific data manifest integrity verified.", fg="green"))
    # This logic for printing general failure needs to be careful not to duplicate messages
    # if a specific error was already added to errors_found_list for data.
    elif Path(settings.DATA_MANIFEST_PATH).exists() and Path(settings.INPUT_DATA_PATH).exists():
        is_data_error_already_logged = any(
            err.get("category") in [
                "specific_data_manifest_tampered", "specific_data_manifest_error",
                "data_file_missing_for_specific_manifest", "specific_data_manifest_missing",
                "specific_data_manifest_exception"
            ] for err in errors_found_list if isinstance(err, dict)
        )
        if not is_data_error_already_logged:
             click.echo(click.style("❌ Specific data manifest integrity check failed (unknown reason).", fg="red"))


    if errors_found_list:
        final_message = "Verification process completed with errors."
        # Construct summary message parts
        summary_parts = []
        if not code_integrity_passed: summary_parts.append("Code integrity FAILED.")

        data_related_error_categories = [
            "data_file_missing_for_specific_manifest", "specific_data_manifest_missing",
            "specific_data_manifest_tampered", "specific_data_manifest_error",
            "specific_data_manifest_exception"
        ]
        if any(isinstance(e, dict) and e.get("category") in data_related_error_categories for e in errors_found_list):
            if not data_integrity_passed: # Only add this part if data integrity explicitly failed or couldn't be determined
                 summary_parts.append("Specific Data Manifest integrity FAILED or could not be verified.")

        if summary_parts:
            final_message += " ".join(summary_parts)

        raise VerificationError(final_message,
                                {"summary_of_errors": errors_found_list,
                                 "overall_code_integrity_passed": code_integrity_passed,
                                 "overall_data_integrity_passed": data_integrity_passed})
    else: # Implies both code_integrity_passed and data_integrity_passed are True
        click.echo(click.style("\n👍 Overall verification passed (Code Integrity + Specific Data Manifest).", fg="green", bold=True))

if __name__ == "__main__":
    cli()
