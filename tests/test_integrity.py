# tests/test_integrity.py
import json
import subprocess
from pathlib import Path
import os
import shutil # For cleaning up

# Helper to get project root, assuming tests are run from project root or /app in Docker
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "verify_integrity.py"
MANIFEST_PATH = PROJECT_ROOT / "sovereign_manifest.json" # Default manifest location

def run_script(command: str, cwd=str(PROJECT_ROOT)):
    """Helper to run the verify_integrity.py script."""
    # Ensure the script path is absolute or correctly relative to cwd
    script_abs_path = Path(cwd) / "scripts" / "verify_integrity.py"
    if not script_abs_path.exists(): # Fallback if script is at PROJECT_ROOT/scripts
        script_abs_path = SCRIPT_PATH

    return subprocess.run(
        ["python", str(script_abs_path), command],
        capture_output=True, text=True, cwd=cwd
    )

def setup_test_environment(tmp_path_factory):
    """Creates a temporary isolated project structure for testing the script."""
    test_proj_root = tmp_path_factory.mktemp("integrity_test_project")

    dirs_to_copy = ["src", "scripts"]
    for dir_to_copy in dirs_to_copy:
        source_dir = PROJECT_ROOT / dir_to_copy
        target_dir = test_proj_root / dir_to_copy
        if source_dir.exists():
            shutil.copytree(source_dir, target_dir)
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            if not list(target_dir.iterdir()): # Create dummy if empty after potential creation
                 (target_dir / f"dummy_{dir_to_copy}.py").write_text("#dummy")

    # Ensure a dummy 'tests' directory exists for consistent manifest generation if script includes it
    tests_dir_target = test_proj_root / "tests"
    if not tests_dir_target.exists():
        tests_dir_target.mkdir(exist_ok=True)
        if not list(tests_dir_target.iterdir()):
            (tests_dir_target / "dummy_tests.py").write_text("#dummy_test")

    return test_proj_root


def test_generate_manifest(tmp_path_factory):
    test_dir = setup_test_environment(tmp_path_factory)
    manifest_file = test_dir / "sovereign_manifest.json"

    if manifest_file.exists():
        manifest_file.unlink()

    result = run_script("generate", cwd=str(test_dir))
    # print(f"Generate STDOUT: {result.stdout}")
    # print(f"Generate STDERR: {result.stderr}")

    assert result.returncode == 0, f"Generate script should exit successfully. STDERR: {result.stderr}"
    assert manifest_file.exists(), "Manifest file should be created."

    with open(manifest_file, "r") as f:
        manifest = json.load(f)

    assert "manifest_version" in manifest
    assert "timestamp" in manifest
    assert "files" in manifest
    assert "git_info" in manifest

    assert any("src" in key for key in manifest["files"]), "Should contain files from src/"
    assert any("scripts" in key for key in manifest["files"]), "Should contain files from scripts/"

    # Check for a specific known file from the copied structure
    assert str(Path("scripts") / "verify_integrity.py") in manifest["files"]

    for file_path, file_hash in manifest["files"].items():
        assert file_hash.startswith("sha256:"), f"Hash for {file_path} should start with sha256:"
        assert len(file_hash.split(":")[1]) == 64, f"Hash for {file_path} should be 64 hex chars."


def test_verify_integrity_success(tmp_path_factory):
    test_dir = setup_test_environment(tmp_path_factory)

    gen_result = run_script("generate", cwd=str(test_dir))
    assert gen_result.returncode == 0, f"Manifest generation failed for success test setup. STDERR: {gen_result.stderr}"
    assert (test_dir / "sovereign_manifest.json").exists()

    verify_result = run_script("verify", cwd=str(test_dir))
    # print(f"Verify (Success) STDOUT: {verify_result.stdout}")
    # print(f"Verify (Success) STDERR: {verify_result.stderr}")

    assert verify_result.returncode == 0, f"Verify script should exit successfully on intact codebase. STDERR: {verify_result.stderr}"
    assert "✅ Codebase integrity (files and signature if present) verified successfully." in verify_result.stdout


def test_verify_integrity_failure_tampered_file(tmp_path_factory):
    test_dir = setup_test_environment(tmp_path_factory)

    gen_result = run_script("generate", cwd=str(test_dir))
    assert gen_result.returncode == 0
    manifest_file_path = test_dir / "sovereign_manifest.json"
    assert manifest_file_path.exists()

    file_to_tamper_rel_path = None
    with open(manifest_file_path, "r") as f:
        manifest_content = json.load(f)
        if manifest_content["files"]:
            # Try to find a specific, predictable file to tamper with
            if str(Path("src") / "main.py") in manifest_content["files"]:
                 file_to_tamper_rel_path = str(Path("src") / "main.py")
            elif str(Path("scripts") / "verify_integrity.py") in manifest_content["files"]:
                 file_to_tamper_rel_path = str(Path("scripts") / "verify_integrity.py")
            else: # Fallback to first file if specific ones not found (e.g. if dummy files were used)
                file_to_tamper_rel_path = list(manifest_content["files"].keys())[0]

    assert file_to_tamper_rel_path is not None, "No files found in manifest to tamper with."
    file_to_tamper_abs_path = test_dir / file_to_tamper_rel_path

    assert file_to_tamper_abs_path.exists(), f"File to tamper ({file_to_tamper_abs_path}) does not exist."

    with open(file_to_tamper_abs_path, "a") as f:
        f.write("\n# This is a malicious change for testing integrity failure.")

    verify_result = run_script("verify", cwd=str(test_dir))
    # print(f"Verify (Tamper) STDERR: {verify_result.stderr}")

    assert verify_result.returncode != 0, "Verify script should exit with non-zero on tampering."
    assert "❌ File integrity verification failed:" in verify_result.stderr
    assert f"- {file_to_tamper_rel_path} → CHANGED" in verify_result.stderr


def test_verify_integrity_failure_missing_file(tmp_path_factory):
    test_dir = setup_test_environment(tmp_path_factory)

    gen_result = run_script("generate", cwd=str(test_dir))
    assert gen_result.returncode == 0
    manifest_file_path = test_dir / "sovereign_manifest.json"
    assert manifest_file_path.exists()

    file_to_remove_rel_path = None
    with open(manifest_file_path, "r") as f:
        manifest_content = json.load(f)
        if manifest_content["files"]:
            if str(Path("src") / "logger.py") in manifest_content["files"]: # Pick a less critical file
                 file_to_remove_rel_path = str(Path("src") / "logger.py")
            else:
                 file_to_remove_rel_path = list(manifest_content["files"].keys())[0]

    assert file_to_remove_rel_path is not None, "No files found in manifest to remove."
    file_to_remove_abs_path = test_dir / file_to_remove_rel_path

    assert file_to_remove_abs_path.exists(), f"File to remove ({file_to_remove_abs_path}) does not exist."
    file_to_remove_abs_path.unlink()

    verify_result = run_script("verify", cwd=str(test_dir))
    # print(f"Verify (Missing) STDERR: {verify_result.stderr}")

    assert verify_result.returncode != 0, "Verify script should exit with non-zero on missing file."
    assert "❌ File integrity verification failed:" in verify_result.stderr
    # The script checks manifest files first, then scans disk. So a file in manifest but not on disk is MISSING.
    assert f"- {file_to_remove_rel_path} → MISSING" in verify_result.stderr # Corrected message

def test_verify_integrity_failure_untracked_file(tmp_path_factory):
    test_dir = setup_test_environment(tmp_path_factory)

    gen_result = run_script("generate", cwd=str(test_dir))
    assert gen_result.returncode == 0
    assert (test_dir / "sovereign_manifest.json").exists()

    untracked_file_path = test_dir / "src" / "untracked_file.py"
    untracked_file_path.write_text("# This file is not in the manifest.")

    verify_result = run_script("verify", cwd=str(test_dir))
    # print(f"Verify (Untracked) STDERR: {verify_result.stderr}")

    assert verify_result.returncode != 0, "Verify script should exit with non-zero on untracked file."
    assert "❌ File integrity verification failed:" in verify_result.stderr
    assert f"- {str(Path('src') / 'untracked_file.py')} → UNTRACKED" in verify_result.stderr

# Test for generate-keys command
def test_generate_keys_command(tmp_path_factory):
    test_dir = setup_test_environment(tmp_path_factory)
    priv_key_path = test_dir / ".private_signing_key.pem"
    pub_key_path = test_dir / ".public_signing_key.pem"

    if priv_key_path.exists(): priv_key_path.unlink()
    if pub_key_path.exists(): pub_key_path.unlink()

    result = run_script("generate-keys", cwd=str(test_dir))
    # print(f"Generate-keys STDOUT: {result.stdout}")
    # print(f"Generate-keys STDERR: {result.stderr}")

    assert result.returncode == 0, f"generate-keys script should exit successfully. STDERR: {result.stderr}"
    assert "🔑 New ECDSA key pair generated:" in result.stdout
    assert priv_key_path.exists(), "Private key file should be created."
    assert pub_key_path.exists(), "Public key file should be created."
    assert priv_key_path.stat().st_size > 0
    assert pub_key_path.stat().st_size > 0

# Test for signing and signature verification (basic, assumes keys are generated)
def test_signed_manifest_verification(tmp_path_factory):
    test_dir = setup_test_environment(tmp_path_factory)
    manifest_file = test_dir / "sovereign_manifest.json"

    # 1. Generate keys
    key_gen_result = run_script("generate-keys", cwd=str(test_dir))
    assert key_gen_result.returncode == 0, f"Key generation failed. STDERR: {key_gen_result.stderr}"
    assert (test_dir / ".private_signing_key.pem").exists()

    # 2. Generate a (signed) manifest
    gen_result = run_script("generate", cwd=str(test_dir))
    assert gen_result.returncode == 0, f"Manifest generation failed. STDERR: {gen_result.stderr}"
    assert manifest_file.exists()
    with open(manifest_file, "r") as f:
        manifest_data = json.load(f)
    assert "signature" in manifest_data, "Manifest should contain a signature block."
    assert "public_key_pem" in manifest_data["signature"]
    assert "signature_base64" in manifest_data["signature"]

    # 3. Verify the signed manifest
    verify_result = run_script("verify", cwd=str(test_dir))
    # print(f"Verify (Signed) STDOUT: {verify_result.stdout}")
    # print(f"Verify (Signed) STDERR: {verify_result.stderr}")
    assert verify_result.returncode == 0, f"Verification of signed manifest failed. STDERR: {verify_result.stderr}"
    assert "✅ Manifest signature verified successfully." in verify_result.stdout
    assert "✅ Codebase integrity (files and signature if present) verified successfully." in verify_result.stdout

    # 4. Tamper with the manifest content (after signing) and expect signature verification to fail
    with open(manifest_file, "r") as f:
        tampered_manifest_data = json.load(f)

    # Add a fake file entry (modifies content after signing)
    tampered_manifest_data["files"]["tampered_entry.txt"] = "sha256:fakehash"
    with open(manifest_file, "w") as f:
        json.dump(tampered_manifest_data, f, indent=2)

    verify_tampered_sig_result = run_script("verify", cwd=str(test_dir))
    # print(f"Verify (Tampered Sig) STDOUT: {verify_tampered_sig_result.stdout}")
    # print(f"Verify (Tampered Sig) STDERR: {verify_tampered_sig_result.stderr}")
    assert verify_tampered_sig_result.returncode != 0, "Verification of tampered signature should fail."
    assert "❌ Error: Manifest signature is invalid!" in verify_tampered_sig_result.stderr # Error from script

    # Cleanup keys for hygiene if other tests run in same root (though tmp_path isolates)
    if (test_dir / ".private_signing_key.pem").exists():
        (test_dir / ".private_signing_key.pem").unlink()
    if (test_dir / ".public_signing_key.pem").exists():
        (test_dir / ".public_signing_key.pem").unlink()
