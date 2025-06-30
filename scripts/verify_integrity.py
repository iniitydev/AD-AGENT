# scripts/verify_integrity.py
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
import argparse
import sys

# Cryptography for signing
from cryptography.hazmat.primitives import hashes as crypto_hashes # Alias to avoid conflict with hashlib module
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from typing import Optional # Import Optional
import base64 # Import base64

# Attempt to import git, but make it optional
try:
    import git
    GIT_PYTHON_AVAILABLE = True
except ImportError:
    GIT_PYTHON_AVAILABLE = False

# --- Configuration for Signing (placeholders, manage keys securely) ---
PRIVATE_KEY_PATH = Path(".private_signing_key.pem") # Default path for private key
# PUBLIC_KEY_PATH = Path(".public_signing_key.pem") # Public key can be derived or stored

def load_private_key(key_path: Path = PRIVATE_KEY_PATH) -> Optional[ec.EllipticCurvePrivateKey]:
    """Loads an ECDSA private key from a PEM file."""
    if not key_path.exists():
        print(f"Warning: Private key for signing not found at {key_path}. Manifest will not be signed.", file=sys.stderr)
        return None
    try:
        with open(key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None # Add password handling if key is encrypted
            )
        if not isinstance(private_key, ec.EllipticCurvePrivateKey):
            print(f"Warning: Key at {key_path} is not a valid ECDSA private key. Manifest will not be signed.", file=sys.stderr)
            return None
        return private_key
    except Exception as e:
        print(f"Warning: Could not load private key from {key_path}: {e}. Manifest will not be signed.", file=sys.stderr)
        return None

def calculate_file_hash(filepath):
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return None

def _get_manifest_content_for_signing(manifest_dict: dict) -> bytes:
    """Helper to get canonical JSON string of manifest excluding signature for signing/verification."""
    temp_manifest = manifest_dict.copy()
    temp_manifest.pop("signature", None) # Remove signature if it exists
    # Sort keys for a canonical representation before signing
    return json.dumps(temp_manifest, sort_keys=True, indent=2).encode('utf-8')


def sign_manifest_dict(manifest_dict: dict, private_key: ec.EllipticCurvePrivateKey) -> Optional[dict]:
    """Signs the manifest data (dictionary) and adds signature block."""
    if not private_key:
        return None # Cannot sign

    manifest_data_bytes = _get_manifest_content_for_signing(manifest_dict)

    signature_bytes = private_key.sign(
        manifest_data_bytes,
        ec.ECDSA(crypto_hashes.SHA256()) # Use SHA256 for signature hashing
    )

    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    manifest_dict["signature"] = {
        "algorithm": "ECDSA-SHA256", # Based on hash used with ECDSA
        "key_algorithm": private_key.curve.name, # e.g., "secp384r1" if that's the curve
        "public_key_pem": public_key_pem, # Store public key in PEM format
        "signature_base64": base64.b64encode(signature_bytes).decode('utf-8')
    }
    return manifest_dict


def verify_manifest_signature(manifest_dict: dict) -> bool:
    """Verifies the signature in the manifest dictionary."""
    if "signature" not in manifest_dict:
        print("Warning: No signature block found in manifest. Cannot verify signature.", file=sys.stderr)
        return False # Or True if unsigned manifests are permissible by policy

    signature_block = manifest_dict["signature"]
    try:
        public_key_pem = signature_block["public_key_pem"].encode('utf-8')
        signature_bytes = base64.b64decode(signature_block["signature_base64"])

        public_key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            print("Error: Public key in manifest is not a valid ECDSA public key.", file=sys.stderr)
            return False

        manifest_data_bytes = _get_manifest_content_for_signing(manifest_dict)

        public_key.verify(
            signature_bytes,
            manifest_data_bytes,
            ec.ECDSA(crypto_hashes.SHA256())
        )
        print("✅ Manifest signature verified successfully.")
        return True
    except InvalidSignature:
        print("❌ Error: Manifest signature is invalid!", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error during signature verification: {e}", file=sys.stderr)
        return False


def generate_manifest(project_root="."):
    project_root_path = Path(project_root).resolve()
    manifest_file_path = project_root_path / 'sovereign_manifest.json'

    manifest = {
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
        except Exception as e:
            manifest["git_info"]["error"] = f"Could not retrieve git info: {str(e)}"
    else:
        manifest["git_info"]["error"] = "GitPython not installed."

    project_dirs = ['src', 'tests', 'scripts']
    for dir_name in project_dirs:
        current_scan_dir = project_root_path / dir_name
        if not current_scan_dir.is_dir(): continue
        for path in current_scan_dir.rglob('*'):
            if path.is_file() and path.name != 'sovereign_manifest.json' and not path.name.startswith('.'):
                if path.suffix == ".pyc" or "__pycache__" in str(path): continue
                file_hash = calculate_file_hash(path)
                if file_hash:
                    relative_path = str(path.relative_to(project_root_path))
                    manifest["files"][relative_path] = f"sha256:{file_hash}"

    # Attempt to sign the manifest
    private_key = load_private_key() # Uses default PRIVATE_KEY_PATH
    if private_key:
        signed_manifest_dict = sign_manifest_dict(manifest, private_key)
        if signed_manifest_dict:
            manifest = signed_manifest_dict # Update manifest with signature block
            print("ℹ️ Manifest signed.")
        else:
            print("Warning: Manifest signing failed, proceeding with unsigned manifest.", file=sys.stderr)
    else:
        print("ℹ️ No private key loaded. Proceeding with an unsigned manifest.")


    try:
        with open(manifest_file_path, 'w') as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        print(f"✅ Manifest generated successfully at {manifest_file_path}")
    except IOError as e:
        print(f"Error writing manifest file: {e}", file=sys.stderr)
        return None
    return manifest


def verify_integrity(project_root="."):
    project_root_path = Path(project_root).resolve()
    manifest_file_path = project_root_path / 'sovereign_manifest.json'

    try:
        with open(manifest_file_path, 'r') as f:
            expected_manifest = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Manifest file not found at {manifest_file_path}", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Error: Could not parse manifest file {manifest_file_path}: {e}", file=sys.stderr)
        return False

    # Verify signature first (if present)
    signature_ok = True # Assume OK if no signature block
    if "signature" in expected_manifest:
        signature_ok = verify_manifest_signature(expected_manifest)
        if not signature_ok:
             # verify_manifest_signature prints detailed error
             return False # Fail fast if signature is invalid
    else:
        print("⚠️ Warning: Manifest is not signed. Integrity check based on content hashes only.", file=sys.stderr)


    # ... (Git info verification - keep as is, or make more robust) ...
    if GIT_PYTHON_AVAILABLE and "git_info" in expected_manifest and expected_manifest["git_info"].get("commit"):
        # (Same git verification as before)
        pass


    failed_files = []
    manifest_files_set = set(expected_manifest.get("files", {}).keys())
    found_files_set = set()

    for dir_name in ['src', 'tests', 'scripts']:
        current_scan_dir = project_root_path / dir_name
        if not current_scan_dir.is_dir(): continue
        for path in current_scan_dir.rglob('*'):
            if path.is_file() and path.name != 'sovereign_manifest.json' and not path.name.startswith('.'):
                if path.suffix == ".pyc" or "__pycache__" in str(path): continue

                relative_path_str = str(path.relative_to(project_root_path))
                found_files_set.add(relative_path_str)
                expected_hash_with_algo = expected_manifest.get("files", {}).get(relative_path_str)

                if not expected_hash_with_algo:
                    failed_files.append((relative_path_str, "UNTRACKED"))
                    continue

                try:
                    algo, expected_hash_val = expected_hash_with_algo.split(":", 1)
                    if algo != "sha256":
                        failed_files.append((relative_path_str, f"UNSUPPORTED_ALGO ({algo})"))
                        continue
                except ValueError:
                    failed_files.append((relative_path_str, "MALFORMED_HASH"))
                    continue

                actual_hash = calculate_file_hash(path)
                if not actual_hash:
                    failed_files.append((relative_path_str, "READ_ERROR"))
                elif actual_hash != expected_hash_val:
                    failed_files.append((relative_path_str, "CHANGED"))

    missing_from_disk = manifest_files_set - found_files_set
    for missing_file_rel_path in missing_from_disk:
        failed_files.append((missing_file_rel_path, "MISSING"))

    if failed_files:
        print("❌ File integrity verification failed:", file=sys.stderr)
        for path_str, status in failed_files:
            print(f"- {path_str} → {status}", file=sys.stderr)
        return False

    if not signature_ok: # If signature failed earlier but file hashes were checked
        print("❌ Overall integrity check failed due to invalid signature, even if file hashes match.", file=sys.stderr)
        return False

    print("✅ Codebase integrity (files and signature if present) verified successfully.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sovereign Integrity Tool')
    parser.add_argument('command', choices=['generate', 'verify', 'generate-keys'], help="Command: 'generate' manifest, 'verify' manifest, or 'generate-keys'.")
    # Add option for key path for signing, if desired
    # parser.add_argument('--key', default=str(PRIVATE_KEY_PATH), help="Path to private key for signing.")

    args = parser.parse_args()

    project_root_for_script = Path(".").resolve()

    if args.command == 'generate-keys':
        priv_key = ec.generate_private_key(ec.SECP384R1()) # Example curve
        pub_key = priv_key.public_key()

        priv_pem = priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption() # Or use an algorithm
        )
        pub_pem = pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        priv_key_file = project_root_for_script / ".private_signing_key.pem"
        pub_key_file = project_root_for_script / ".public_signing_key.pem"

        with open(priv_key_file, "wb") as f: f.write(priv_pem)
        with open(pub_key_file, "wb") as f: f.write(pub_pem)
        print(f"🔑 New ECDSA key pair generated:\nPrivate key: {priv_key_file}\nPublic key: {pub_key_file}")
        print("IMPORTANT: Secure the private key. The public key can be shared.")

    elif args.command == 'generate':
        generate_manifest(project_root=str(project_root_for_script))
    elif args.command == 'verify':
        if not verify_integrity(project_root=str(project_root_for_script)):
            sys.exit(1)
