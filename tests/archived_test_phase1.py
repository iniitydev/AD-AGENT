# tests/test_phase1.py
import pytest
from click.testing import CliRunner
from pathlib import Path
import json
import os
from unittest.mock import patch

from src.main import cli # Use the actual CLI entry point
from src.config import Settings, settings as app_settings # Import for test_settings_load and monkeypatching

# valid_environment fixture will be auto-discovered from conftest.py

@pytest.fixture(scope="module")
def cli_runner():
    return CliRunner()

def test_verify_success(cli_runner, valid_environment):
    """Test successful verification scenario"""
    with patch("src.main.perform_code_integrity_check_func") as mock_code_verify, \
         patch("src.main.perform_data_file_manifest_check_func") as mock_data_verify:

        mock_code_verify.return_value = True
        mock_data_verify.return_value = {"status": "verified", "file": valid_environment["INPUT_DATA_PATH"]}

        result = cli_runner.invoke(cli, ["verify"], env=valid_environment)

        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}. Output:\n{result.output}"
        assert "✅ Code integrity script check passed (called by CLI)." in result.output
        assert "✅ Specific data manifest integrity verified." in result.output
        assert "👍 Overall verification passed" in result.output
        mock_code_verify.assert_called_once()
        mock_data_verify.assert_called_once_with(valid_environment["INPUT_DATA_PATH"], valid_environment["DATA_MANIFEST_PATH"])

def test_verify_missing_manifest(cli_runner, valid_environment, tmp_path, monkeypatch):
    """Test missing data manifest scenario"""
    missing_manifest_file = tmp_path / "this_manifest_does_not_exist.json"

    # Use monkeypatch to change the setting for the duration of this test
    original_data_manifest_path = app_settings.DATA_MANIFEST_PATH
    monkeypatch.setattr(app_settings, "DATA_MANIFEST_PATH", str(missing_manifest_file))

    # Create a new env dict for invoke, inheriting from valid_environment but overriding DATA_MANIFEST_PATH
    # This ensures that if Settings() is re-instantiated inside the command, it picks up the new path.
    env_for_test = valid_environment.copy()
    env_for_test["DATA_MANIFEST_PATH"] = str(missing_manifest_file)

    try:
        with patch("src.main.perform_code_integrity_check_func") as mock_code_verify:
            mock_code_verify.return_value = True

            result = cli_runner.invoke(cli, ["verify"], env=env_for_test)

            assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"
            assert "❌ Verification process completed with errors." in result.output
            assert "Specific Data Manifest integrity FAILED or could not be verified." in result.output

            details_json_str = result.output.split("Details:\n", 1)[1]
            error_details = json.loads(details_json_str)

            found_error = False
            for err_item in error_details.get("summary_of_errors", []):
                if err_item.get("category") == "specific_data_manifest_missing":
                    assert err_item["message"] == f"Specific data manifest file not found: {missing_manifest_file}" # Check message
                    assert err_item["details"]["expected_manifest_path"] == str(missing_manifest_file) # Check details
                    found_error = True
                    break
            assert found_error, f"Specific 'specific_data_manifest_missing' error with path not found in {error_details}"
    finally:
        monkeypatch.setattr(app_settings, "DATA_MANIFEST_PATH", original_data_manifest_path)


def test_verify_tampered_data(cli_runner, valid_environment):
    """Test data tampering detection"""
    with patch("src.main.perform_code_integrity_check_func") as mock_code_verify, \
         patch("src.main.perform_data_file_manifest_check_func") as mock_data_verify:

        mock_code_verify.return_value = True
        mock_data_verify.return_value = {
            "status": "tampered",
            "file": valid_environment["INPUT_DATA_PATH"],
            "expected_hash": "original_hash",
            "current_hash": "new_hash"
        }

        result = cli_runner.invoke(cli, ["verify"], env=valid_environment)
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"
        assert "❌ Verification process completed with errors." in result.output
        assert "Specific Data Manifest integrity FAILED or could not be verified." in result.output
        assert "Tampering detected for specific data manifest" in result.output
        assert "new_hash" in result.output

def test_verify_code_failure(cli_runner, valid_environment):
    """Test code verification failure"""
    with patch("src.main.perform_code_integrity_check_func") as mock_code_verify, \
         patch("src.main.perform_data_file_manifest_check_func") as mock_data_verify:

        mock_code_verify.return_value = False
        mock_data_verify.return_value = {"status": "verified"}

        result = cli_runner.invoke(cli, ["verify"], env=valid_environment)
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"
        assert "❌ Verification process completed with errors." in result.output
        assert "Code integrity FAILED." in result.output
        assert "Overall code integrity script reported issues" in result.output

def test_verify_missing_data_file(cli_runner, valid_environment, tmp_path, monkeypatch):
    """Test missing data file scenario"""
    from src.config import settings as app_settings # Import for monkeypatching

    missing_data_file = tmp_path / "this_data_does_not_exist.csv"

    original_input_data_path = app_settings.INPUT_DATA_PATH
    monkeypatch.setattr(app_settings, "INPUT_DATA_PATH", str(missing_data_file))

    # Create an env dict for invoke, ensuring INPUT_DATA_PATH is the missing one
    env_for_test = valid_environment.copy()
    env_for_test["INPUT_DATA_PATH"] = str(missing_data_file)

    # Ensure the manifest that DATA_MANIFEST_PATH points to *does* exist for this test,
    # and it refers to the (now) missing data file.
    # The DATA_MANIFEST_PATH itself is taken from valid_environment via env_for_test.
    manifest_path_for_test = Path(env_for_test["DATA_MANIFEST_PATH"])
    manifest_path_for_test.write_text(json.dumps({"data_input": {"path": str(missing_data_file), "hash_sha256": "anyhash"}}))

    try:
        with patch("src.main.perform_code_integrity_check_func") as mock_code_verify:
            mock_code_verify.return_value = True

            result = cli_runner.invoke(cli, ["verify"], env=env_for_test)

            assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"
            assert "❌ Verification process completed with errors." in result.output
            assert "Specific Data Manifest integrity FAILED or could not be verified." in result.output
            assert f"Data file for specific manifest check not found: {missing_data_file}" in result.output
            assert str(missing_data_file) in result.output # Check path is in details
    finally:
        monkeypatch.setattr(app_settings, "INPUT_DATA_PATH", original_input_data_path)


def test_cli_encrypt_decrypt_flow(cli_runner, tmp_path):
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
    Path(valid_environment["MODEL_OUTPUT_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    Path(valid_environment["MANIFEST_OUTPUT_PATH"]).mkdir(parents=True, exist_ok=True)

    with patch("src.main.run_training_process") as mock_run_training:
        mock_run_training.return_value = True

        result = cli_runner.invoke(cli, [
            "train",
            "--input-data-path", valid_environment["INPUT_DATA_PATH"],
            "--model-output-path", valid_environment["MODEL_OUTPUT_PATH"],
            "--manifest-output-path", valid_environment["MANIFEST_OUTPUT_PATH"]
        ], env=valid_environment)

        assert result.exit_code == 0, f"Train command failed. Output:\n{result.output}"
        assert "Model training finished successfully" in result.output
        mock_run_training.assert_called_once_with(
            input_path_override=valid_environment["INPUT_DATA_PATH"],
            output_path_override=valid_environment["MODEL_OUTPUT_PATH"],
            manifest_dir_override=valid_environment["MANIFEST_OUTPUT_PATH"]
        )

def test_settings_load(valid_environment, cli_runner):
    config_result = cli_runner.invoke(cli, ["config"], env=valid_environment)
    assert config_result.exit_code == 0
    assert f"INPUT_DATA_PATH: {valid_environment['INPUT_DATA_PATH']}" in config_result.output
    assert f"DATA_MANIFEST_PATH: {valid_environment['DATA_MANIFEST_PATH']}" in config_result.output
