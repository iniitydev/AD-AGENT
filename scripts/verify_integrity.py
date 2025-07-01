# scripts/verify_integrity.py
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
import argparse
import sys
import base64 # Ensure base64 is imported
from typing import Optional, Dict, Any, Tuple, List # For type hints

# Cryptography for signing
from cryptography.hazmat.primitives import hashes as crypto_hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

try:
    import git
    GIT_PYTHON_AVAILABLE = True
except ImportError:
    GIT_PYTHON_AVAILABLE = False

PRIVATE_KEY_PATH = Path(".private_signing_key.pem")

def load_private_key(key_path: Path = PRIVATE_KEY_PATH) -> Optional[ec.EllipticCurvePrivateKey]:
    if not key_path.exists():
        # print(f"Warning: Private key for signing not found at {key_path}.", file=sys.stderr)
        return None
    try:
        with open(key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None
            )
        if not isinstance(private_key, ec.EllipticCurvePrivateKey):
            # print(f"Warning: Key at {key_path} is not a valid ECDSA private key.", file=sys.stderr)
            return None
        return private_key
    except Exception as e:
        # print(f"Warning: Could not load private key from {key_path}: {e}.", file=sys.stderr)
        return None

def calculate_file_hash(filepath: Path) -> Optional[str]: # Changed to Path
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        # print(f"Error reading {filepath}: {e}", file=sys.stderr) # Keep for CLI
        return None

def _get_manifest_content_for_signing(manifest_dict: dict) -> bytes:
    temp_manifest = manifest_dict.copy()
    temp_manifest.pop("signature", None)
    return json.dumps(temp_manifest, sort_keys=True, indent=2).encode('utf-8')

def sign_manifest_dict(manifest_dict: dict, private_key: ec.EllipticCurvePrivateKey) -> Optional[dict]:
    if not private_key: return None
    manifest_data_bytes = _get_manifest_content_for_signing(manifest_dict)
    signature_bytes = private_key.sign(
        manifest_data_bytes, ec.ECDSA(crypto_hashes.SHA256())
    )
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    manifest_dict["signature"] = {
        "algorithm": "ECDSA-SHA256",
        "key_algorithm": private_key.curve.name,
        "public_key_pem": public_key_pem,
        "signature_base64": base64.b64encode(signature_bytes).decode('utf-8')
    }
    return manifest_dict

def verify_manifest_signature(manifest_dict: dict) -> Tuple[bool, str]:
    """Returns (bool_verified, status_message_str)"""
    if "signature" not in manifest_dict:
        return True, "Manifest is not signed. Skipping signature verification." # Treat as "verified" if no signature
    signature_block = manifest_dict["signature"]
    try:
        public_key_pem = signature_block["public_key_pem"].encode('utf-8')
        signature_bytes = base64.b64decode(signature_block["signature_base64"])
        public_key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False, "Error: Public key in manifest is not a valid ECDSA public key."
        manifest_data_bytes = _get_manifest_content_for_signing(manifest_dict)
        public_key.verify(
            signature_bytes, manifest_data_bytes, ec.ECDSA(crypto_hashes.SHA256())
        )
        return True, "Manifest signature verified successfully."
    except InvalidSignature:
        return False, "Error: Manifest signature is invalid!"
    except Exception as e:
        return False, f"Error during signature verification: {e}"

def generate_manifest(project_root_str: str = ".", manifest_filename: str = "sovereign_manifest.json") -> Optional[Dict[str, Any]]:
    project_root_path = Path(project_root_str).resolve()
    manifest_file_path = project_root_path / manifest_filename

    manifest: Dict[str, Any] = {
        "manifest_version": "2.5.0",
        "timestamp": datetime.now().isoformat(),
        "files": {},
        "git_info": {}
    }

    if GIT_PYTHON_AVAILABLE:
        try:
            repo = git.Repo(project_root_path, search_parent_directories=True)
            manifest["git_info"] = {
                "commit": str(repo.head.commit),
                "branch": str(repo.active_branch.name if repo.active_branch else "DETACHED_HEAD"),
                "dirty": repo.is_dirty()
            }
        except Exception as e: manifest["git_info"]["error"] = f"Could not retrieve git info: {str(e)}"
    else: manifest["git_info"]["error"] = "GitPython not installed."

    project_dirs = ['src', 'tests', 'scripts']
    for dir_name in project_dirs:
        current_scan_dir = project_root_path / dir_name
        if not current_scan_dir.is_dir(): continue
        for path_obj in current_scan_dir.rglob('*'): # Changed path to path_obj
            if path_obj.is_file() and path_obj.name != manifest_filename and not path_obj.name.startswith('.'):
                if path_obj.suffix == ".pyc" or "__pycache__" in str(path_obj): continue
                file_hash = calculate_file_hash(path_obj)
                if file_hash:
                    relative_path = str(path_obj.relative_to(project_root_path))
                    manifest["files"][relative_path] = f"sha256:{file_hash}"

    private_key = load_private_key(project_root_path / PRIVATE_KEY_PATH.name) # Ensure key path is relative to project root
    if private_key:
        signed_manifest_dict = sign_manifest_dict(manifest, private_key)
        if signed_manifest_dict:
            manifest = signed_manifest_dict
            # print("ℹ️ Manifest signed.") # Keep for CLI
        # else: print("Warning: Manifest signing failed.", file=sys.stderr) # Keep for CLI
    # else: print("ℹ️ No private key loaded. Proceeding with an unsigned manifest.") # Keep for CLI

    try:
        with open(manifest_file_path, 'w') as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        # print(f"✅ Manifest generated successfully at {manifest_file_path}") # Keep for CLI
    except IOError as e:
        # print(f"Error writing manifest file: {e}", file=sys.stderr) # Keep for CLI
        return None # API should get None if write fails
    return manifest # Return the manifest dictionary

def verify_integrity(project_root_str: str = ".", manifest_filename: str = "sovereign_manifest.json") -> Dict[str, Any]:
    project_root_path = Path(project_root_str).resolve()
    manifest_file_path = project_root_path / manifest_filename

    result: Dict[str, Any] = {
        "verified": False,
        "signature_verified": None, # True, False, or "not_present"
        "signature_message": "",
        "files_checked": 0,
        "files_ok": 0,
        "failed_files_details": [], # List of tuples (filepath, status_str)
        "error_message": None
    }

    try:
        with open(manifest_file_path, 'r') as f:
            expected_manifest = json.load(f)
    except FileNotFoundError:
        result["error_message"] = f"Manifest file not found at {manifest_file_path}"
        return result
    except json.JSONDecodeError as e:
        result["error_message"] = f"Could not parse manifest file {manifest_file_path}: {e}"
        return result

    if "signature" in expected_manifest:
        sig_ok, sig_msg = verify_manifest_signature(expected_manifest)
        result["signature_verified"] = sig_ok
        result["signature_message"] = sig_msg
        if not sig_ok: # Fail fast if signature is invalid
            result["error_message"] = "Manifest signature invalid."
            # No need to set result["verified"] = False, it's already default
            return result
    else:
        result["signature_verified"] = "not_present"
        result["signature_message"] = "Manifest is not signed."

    # Git info check (optional, for info/warning only, not hard fail)
    # ... (Can add git check details to result if desired) ...

    failed_files_list: List[Tuple[str, str]] = []
    manifest_files_set = set(expected_manifest.get("files", {}).keys())
    found_files_set = set()
    files_ok_count = 0

    project_dirs = ['src', 'tests', 'scripts']
    for dir_name in project_dirs:
        current_scan_dir = project_root_path / dir_name
        if not current_scan_dir.is_dir(): continue
        for path_obj in current_scan_dir.rglob('*'):
            if path_obj.is_file() and path_obj.name != manifest_filename and not path_obj.name.startswith('.'):
                if path_obj.suffix == ".pyc" or "__pycache__" in str(path_obj): continue

                result["files_checked"] += 1
                relative_path_str = str(path_obj.relative_to(project_root_path))
                found_files_set.add(relative_path_str)
                expected_hash_with_algo = expected_manifest.get("files", {}).get(relative_path_str)

                if not expected_hash_with_algo:
                    failed_files_list.append((relative_path_str, "UNTRACKED"))
                    continue

                try:
                    algo, expected_hash_val = expected_hash_with_algo.split(":", 1)
                    if algo != "sha256":
                        failed_files_list.append((relative_path_str, f"UNSUPPORTED_ALGO ({algo})"))
                        continue
                except ValueError:
                    failed_files_list.append((relative_path_str, "MALFORMED_HASH"))
                    continue

                actual_hash = calculate_file_hash(path_obj)
                if not actual_hash:
                    failed_files_list.append((relative_path_str, "READ_ERROR"))
                elif actual_hash != expected_hash_val:
                    failed_files_list.append((relative_path_str, "CHANGED"))
                else:
                    files_ok_count +=1

    result["files_ok"] = files_ok_count
    missing_from_disk = manifest_files_set - found_files_set
    for missing_file_rel_path in missing_from_disk:
        failed_files_list.append((missing_file_rel_path, "MISSING"))
        result["files_checked"] +=1 # Count it as checked from manifest

    result["failed_files_details"] = [{"path": p, "status": s} for p,s in failed_files_list]

    if not failed_files_list and (result["signature_verified"] is True or result["signature_verified"] == "not_present"):
        result["verified"] = True

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sovereign Integrity Tool')
    parser.add_argument('command', choices=['generate', 'verify', 'generate-keys'],
                        help="Command: 'generate' manifest, 'verify' manifest, or 'generate-keys'.")
    args = parser.parse_args()

    project_root = Path(".").resolve()

    if args.command == 'generate-keys':
        priv_key = ec.generate_private_key(ec.SECP384R1())
        pub_key = priv_key.public_key()
        priv_pem = priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_pem = pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        priv_key_file = project_root / PRIVATE_KEY_PATH.name
        pub_key_file = project_root / (PRIVATE_KEY_PATH.stem + "_pub.pem")
        with open(priv_key_file, "wb") as f: f.write(priv_pem)
        with open(pub_key_file, "wb") as f: f.write(pub_pem)
        print(f"🔑 New ECDSA key pair generated:\nPrivate key: {priv_key_file}\nPublic key: {pub_key_file}")
        print("IMPORTANT: Secure the private key. The public key can be shared or embedded.")

    elif args.command == 'generate':
        print("Generating manifest...")
        generated_manifest = generate_manifest(project_root_str=str(project_root))
        if generated_manifest:
            print(f"✅ Manifest generated successfully at {project_root / 'sovereign_manifest.json'}")
            if "signature" in generated_manifest:
                print("ℹ️ Manifest was signed.")
            else:
                print("⚠️ Manifest was NOT signed (no private key found or error during signing).")
        else:
            print("❌ Manifest generation failed.", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'verify':
        print("Verifying integrity...")
        verification_result = verify_integrity(project_root_str=str(project_root))

        if verification_result.get("error_message"):
            print(f"❌ Verification Pre-check Error: {verification_result['error_message']}", file=sys.stderr)
            sys.exit(1)

        if verification_result["signature_verified"] is True:
            print(f"✅ {verification_result['signature_message']}")
        elif verification_result["signature_verified"] is False:
            print(f"❌ {verification_result['signature_message']}", file=sys.stderr)
        elif verification_result["signature_verified"] == "not_present":
            print(f"⚠️ {verification_result['signature_message']}", file=sys.stderr)

        if verification_result["failed_files_details"]:
            print("❌ File integrity verification failed for some files:", file=sys.stderr)
            for item in verification_result["failed_files_details"]:
                print(f"- {item['path']} → {item['status']}", file=sys.stderr)

        if verification_result["verified"]:
            print("✅ Codebase integrity (files and signature if present) verified successfully.")
        else:
            print("❌ Overall integrity check FAILED.", file=sys.stderr)
            sys.exit(1)
