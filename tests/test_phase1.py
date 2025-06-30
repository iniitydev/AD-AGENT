# tests/test_phase1.py
import pytest
from click.testing import CliRunner
from src.main import cli # Directly import the cli group
from unittest.mock import patch
import json
from pathlib import Path # Ensure Path is imported

# valid_environment fixture will be auto-discovered from conftest.py

@pytest.fixture(scope="module")
def cli_runner():
    return CliRunner()

def test_verify_success(cli_runner, valid_environment):
    """Test successful verification scenario"""
    # valid_environment (from conftest) sets up necessary files and env vars
    # The env vars are passed to invoke, and Settings() inside 'verify' should pick them up.
    with patch("src.main.verify_code_integrity_script") as mock_code_verify, \
         patch("src.main.verify_data_integrity_func") as mock_data_verify:

        mock_code_verify.return_value = True
        mock_data_verify.return_value = {"status": "verified", "file": valid_environment["INPUT_DATA_PATH"]}

        result = cli_runner.invoke(cli, ["verify"], env=valid_environment)

        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}. Output:\n{result.output}"
        assert "✅ Code integrity verified" in result.output
        assert "✅ Data integrity verified" in result.output
        assert "👍 Overall verification passed" in result.output # This is the success message
        mock_code_verify.assert_called_once()
        mock_data_verify.assert_called_once_with(valid_environment["INPUT_DATA_PATH"], valid_environment["DATA_MANIFEST_PATH"])

def test_verify_missing_manifest(cli_runner, valid_environment): # Removed tmp_path, valid_env creates paths
    """Test missing data manifest scenario"""
    env_for_test = valid_environment.copy()
    # valid_environment creates DATA_MANIFEST_PATH. We need to ensure it points to a non-existent file for this test.
    # The conftest.py fixture creates DATA_MANIFEST_PATH. To test missing, we can unlink it.
    manifest_to_remove = Path(env_for_test["DATA_MANIFEST_PATH"])
    if manifest_to_remove.exists():
        manifest_to_remove.unlink()

    with patch("src.main.verify_code_integrity_script") as mock_code_verify:
        mock_code_verify.return_value = True

        result = cli_runner.invoke(cli, ["verify"], env=env_for_test)

        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"
        # The VerificationError's message is "Verification failed for: data_manifest_missing"
        # The details part will contain the specific reason.
        assert "❌ Verification failed for: data_manifest_missing" in result.output
        assert "Manifest not found" in result.output # This is part of the details
        assert str(manifest_to_remove) in result.output # Path should be in details

def test_verify_tampered_data(cli_runner, valid_environment):
    """Test data tampering detection"""
    with patch("src.main.verify_code_integrity_script") as mock_code_verify, \
         patch("src.main.verify_data_integrity_func") as mock_data_verify:

        mock_code_verify.return_value = True
        mock_data_verify.return_value = {
            "status": "tampered",
            "file": "data.csv", # Matching the filename from valid_environment
            "current_sha256": "new_hash",
            "recorded_sha256": "original_hash"
        }

        result = cli_runner.invoke(cli, ["verify"], env=valid_environment)
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"
        assert "❌ Verification failed for: data_integrity_check_failed" in result.output
        assert "Data integrity check failed: tampered" in result.output
        assert "new_hash" in result.output

def test_verify_code_failure(cli_runner, valid_environment):
    """Test code verification failure"""
    with patch("src.main.verify_code_integrity_script") as mock_code_verify, \
         patch("src.main.verify_data_integrity_func") as mock_data_verify:

        mock_code_verify.side_effect = Exception("Missing sovereign_manifest.json") # Simulate script error
        mock_data_verify.return_value = {"status": "verified"}

        result = cli_runner.invoke(cli, ["verify"], env=valid_environment)
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"
        assert "❌ Verification failed for: code_integrity_exception" in result.output
        assert "Missing sovereign_manifest.json" in result.output

def test_verify_missing_data_file(cli_runner, valid_environment):
    """Test missing data file scenario"""
    env_for_test = valid_environment.copy()
    data_file_to_remove = Path(env_for_test["INPUT_DATA_PATH"])
    if data_file_to_remove.exists():
        data_file_to_remove.unlink()

    # Ensure the manifest file still exists for this test
    Path(env_for_test["DATA_MANIFEST_PATH"]).write_text(json.dumps({"data_input": {"path": str(data_file_to_remove), "hash_sha256": "anyhash"}}))

    with patch("src.main.verify_code_integrity_script") as mock_code_verify:
        mock_code_verify.return_value = True

        result = cli_runner.invoke(cli, ["verify"], env=env_for_test)

        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"
        assert "❌ Verification failed for: data_file_missing" in result.output
        assert "Data file not found" in result.output
        assert str(data_file_to_remove) in result.output


# Keep existing encrypt/decrypt and train command tests
def test_cli_encrypt_decrypt_flow(cli_runner, tmp_path): # tmp_path from pytest
    plain_file = tmp_path / "encrypt_me.txt"
    plain_file.write_text("Super secret sovereign data for encryption test!")

    encrypted_file_path = tmp_path / "encrypt_me.txt.enc"
    decrypted_file_path = tmp_path / "encrypt_me.txt.dec"
    password = "testpassword123"

    encrypt_result = cli_runner.invoke(cli, [
        "encrypt", "--input-file", str(plain_file), "--output-file", str(encrypted_file_path),
    ], input=f"{password}\n{password}\n")
    assert encrypt_result.exit_code == 0, f"Encrypt CLI failed: {encrypt_result.output}"
    assert encrypted_file_path.exists()

    decrypt_result = cli_runner.invoke(cli, [
        "decrypt", "--input-file", str(encrypted_file_path), "--output-file", str(decrypted_file_path),
    ], input=f"{password}\n")
    assert decrypt_result.exit_code == 0, f"Decrypt CLI failed: {decrypt_result.output}"
    assert decrypted_file_path.exists()
    assert plain_file.read_text() == decrypted_file_path.read_text()

def test_train_command_runs(cli_runner, valid_environment):
    # valid_environment provides paths via env vars.
    Path(valid_environment["MODEL_OUTPUT_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    Path(valid_environment["MANIFEST_OUTPUT_PATH"]).mkdir(parents=True, exist_ok=True)

    with patch("src.main.run_training_process") as mock_run_training:
        mock_run_training.return_value = True

        # Pass paths as CLI options now, not just relying on env for settings inside train
        result = cli_runner.invoke(cli, [
            "train",
            "--input-data-path", valid_environment["INPUT_DATA_PATH"],
            "--model-output-path", valid_environment["MODEL_OUTPUT_PATH"],
            "--manifest-output-path", valid_environment["MANIFEST_OUTPUT_PATH"]
        ], env=valid_environment) # env still useful if train internal logic re-instantiates Settings

        assert result.exit_code == 0, f"Train command failed. Output:\n{result.output}"
        assert "Model training finished successfully" in result.output
        mock_run_training.assert_called_once_with(
            input_path_override=valid_environment["INPUT_DATA_PATH"],
            output_path_override=valid_environment["MODEL_OUTPUT_PATH"],
            manifest_dir_override=valid_environment["MANIFEST_OUTPUT_PATH"]
        )

def test_settings_load(valid_environment, cli_runner):
    # Use the "config" command which reloads settings
    result = cli_runner.invoke(cli, ["config"], env=valid_environment)
    assert result.exit_code == 0
    assert f"INPUT_DATA_PATH: {valid_environment['INPUT_DATA_PATH']}" in result.output
    assert f"DATA_MANIFEST_PATH: {valid_environment['DATA_MANIFEST_PATH']}" in result.output
