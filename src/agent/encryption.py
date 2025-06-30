# src/agent/encryption.py
import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Tuple, Optional # Added Optional
from pathlib import Path # For file operations if needed in __main__

from src.logger import get_logger
from src.config import settings # For ENCRYPTION_KEY_DERIVATION_ITERATIONS

logger = get_logger(__name__)

# WARNING: For production, key management is critical.
# Storing keys derived from passwords directly or passwords themselves in .env is not ideal.
# Consider environment-specific key management solutions or a dedicated secrets manager.

def generate_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Generates a secure encryption key from a password and salt using PBKDF2HMAC-SHA256.
    If salt is not provided, a new one is generated.
    Returns the derived key (32 bytes for AES-256) and the salt used.
    """
    if salt is None:
        salt = os.urandom(16)  # AESGCM standard nonce size is 12 bytes, salt can be 16 bytes.

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # For AES-256
        salt=salt,
        iterations=settings.ENCRYPTION_KEY_DERIVATION_ITERATIONS,
    )
    key = kdf.derive(password.encode('utf-8'))
    return key, salt

def sovereign_encrypt(data: bytes, key: bytes) -> bytes:
    """
    Encrypts data using AES-GCM with the provided key.
    Prepends a 12-byte nonce to the ciphertext.
    """
    if not isinstance(data, bytes):
        raise TypeError("Data to encrypt must be bytes.")
    if len(key) != 32: # AES-256 key
        raise ValueError("Encryption key must be 32 bytes long for AES-256.")

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # AES-GCM standard nonce size
    ciphertext = aesgcm.encrypt(nonce, data, None) # No associated data
    return nonce + ciphertext # Prepend nonce to ciphertext

def sovereign_decrypt(token: bytes, key: bytes) -> bytes:
    """
    Decrypts data using AES-GCM with the provided key.
    Assumes the first 12 bytes of the token are the nonce.
    """
    if not isinstance(token, bytes):
        raise TypeError("Token to decrypt must be bytes.")
    if len(key) != 32:
        raise ValueError("Decryption key must be 32 bytes long for AES-256.")
    if len(token) < 13: # At least 12 bytes for nonce + 1 byte for data
        raise ValueError("Token is too short to contain a nonce and data.")

    nonce = token[:12]
    ciphertext = token[12:]
    aesgcm = AESGCM(key)
    try:
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_data
    except Exception as e: # Catches InvalidTag from cryptography if decryption fails
        logger.error(f"Decryption failed. This could be due to an incorrect key, corrupted data, or invalid token structure: {e}")
        # Do not expose too much detail about the error in production to avoid oracle attacks
        raise ValueError("Decryption failed. Invalid key or corrupted data.") from e


def encrypt_file(file_path: str, password: str, encrypted_file_path: Optional[str] = None):
    """Encrypts a file using a password and saves it. Salt is prepended to the encrypted file."""
    p_file_path = Path(file_path)
    if encrypted_file_path is None:
        p_encrypted_file_path = p_file_path.with_suffix(p_file_path.suffix + '.enc')
    else:
        p_encrypted_file_path = Path(encrypted_file_path)

    logger.info(f"Encrypting file {p_file_path} to {p_encrypted_file_path}")
    try:
        key, salt = generate_key_from_password(password) # Salt is generated here

        with open(p_file_path, "rb") as f_in:
            data_to_encrypt = f_in.read()

        encrypted_content_with_nonce = sovereign_encrypt(data_to_encrypt, key)

        # Prepend salt to the final encrypted file content
        # Format: [16_bytes_salt][12_bytes_nonce][encrypted_data]
        with open(p_encrypted_file_path, "wb") as f_out:
            f_out.write(salt)
            f_out.write(encrypted_content_with_nonce)
        logger.info(f"File encrypted and saved to {p_encrypted_file_path}. Salt is included in the file.")
        logger.info(f"Salt (hex) for recovery if needed separately (though it's in the file): {salt.hex()}")

    except FileNotFoundError:
        logger.error(f"File not found for encryption: {file_path}")
        raise
    except Exception as e:
        logger.error(f"File encryption failed for {file_path}: {e}", exc_info=True)
        raise
    return str(p_encrypted_file_path), salt # Return path and salt for CLI


def decrypt_file(encrypted_file_path: str, password: str, output_file_path: Optional[str] = None):
    """Decrypts a file using a password. Assumes salt is prepended in the encrypted file."""
    p_encrypted_file_path = Path(encrypted_file_path)

    if output_file_path is None:
        if not str(p_encrypted_file_path).endswith(".enc"):
            logger.warning(f"Encrypted file path {p_encrypted_file_path} does not end with .enc. Output path may be unexpected.")
            p_output_file_path = p_encrypted_file_path.with_name(p_encrypted_file_path.stem) # Try to remove last suffix
        else:
            p_output_file_path = Path(str(p_encrypted_file_path)[:-4]) # Remove .enc
    else:
        p_output_file_path = Path(output_file_path)

    p_output_file_path.parent.mkdir(parents=True, exist_ok=True)


    logger.info(f"Decrypting file {p_encrypted_file_path} to {p_output_file_path}")
    try:
        with open(p_encrypted_file_path, "rb") as f_in:
            salt = f_in.read(16) # Read the salt (first 16 bytes)
            encrypted_data_with_nonce = f_in.read()

        if len(salt) < 16:
            raise ValueError("Encrypted file is too short to contain a valid salt.")

        key, _ = generate_key_from_password(password, salt) # Regenerate key using the read salt

        decrypted_content = sovereign_decrypt(encrypted_data_with_nonce, key)

        with open(p_output_file_path, "wb") as f_out:
            f_out.write(decrypted_content)
        logger.info(f"File decrypted and saved to {p_output_file_path}")

    except FileNotFoundError:
        logger.error(f"Encrypted file not found: {encrypted_file_path}")
        raise
    except ValueError as ve: # Catch specific ValueError from sovereign_decrypt or salt check
        logger.error(f"File decryption failed: {ve}")
        raise
    except Exception as e:
        logger.error(f"File decryption failed for {encrypted_file_path}: {e}", exc_info=True)
        raise
    return str(p_output_file_path)


if __name__ == "__main__":
    import click # For potential CLI-like testing within __main__
    logger.info("--- Testing Encryption/Decryption Module ---")

    # Test key generation
    test_password = "myVerySecretPassword123!"
    logger.info(f"Using test password: {test_password}")
    logger.info(f"Key derivation iterations from settings: {settings.ENCRYPTION_KEY_DERIVATION_ITERATIONS}")

    key1, salt1 = generate_key_from_password(test_password)
    logger.info(f"Generated Key1 (first 5 bytes hex): {key1[:5].hex()}...")
    logger.info(f"Generated Salt1 (hex): {salt1.hex()}")

    key2, salt2 = generate_key_from_password(test_password, salt=salt1) # Using same salt
    assert key1 == key2, "Keys generated with the same password and salt should be identical."
    logger.info("Key regeneration with same salt successful.")

    # Test data encryption/decryption
    original_text = "This is some highly sensitive sovereign data! £$€"
    original_bytes = original_text.encode('utf-8')
    logger.info(f"Original data for byte test: '{original_text}'")

    try:
        encrypted_bytes_with_nonce = sovereign_encrypt(original_bytes, key1)
        logger.info(f"Encrypted data with nonce (first 20 bytes of token): {encrypted_bytes_with_nonce[:20].hex()}...")

        decrypted_bytes = sovereign_decrypt(encrypted_bytes_with_nonce, key1)
        decrypted_text = decrypted_bytes.decode('utf-8')
        assert original_text == decrypted_text, "Decrypted text does not match original."
        logger.info(f"Decrypted data: '{decrypted_text}'")
        logger.info(click.style("✅ Byte-level encryption/decryption test successful.", fg="green"))
    except Exception as e:
        logger.error(click.style(f"❌ Byte-level encryption/decryption test FAILED: {e}", fg="red"), exc_info=True)

    # File encryption/decryption test
    test_file_dir = Path("./temp_encryption_test_files_module") # Unique name
    test_file_dir.mkdir(parents=True, exist_ok=True)

    original_file_path = test_file_dir / "test_plain_module.txt"
    # Encrypted file path will be auto-generated with .enc by encrypt_file function

    logger.info(f"--- Testing File Encryption/Decryption ---")
    try:
        original_file_content = "Contents of the super secret file for testing file encryption. Includes Unicode: éàçüö."
        with open(original_file_path, "w", encoding='utf-8') as f:
            f.write(original_file_content)
        logger.info(f"Created original test file: {original_file_path}")

        # Encrypt
        encrypted_file_path_actual, used_salt = encrypt_file(str(original_file_path), test_password)
        logger.info(f"Encryption complete. Encrypted file: {encrypted_file_path_actual}, Salt used (hex): {used_salt.hex()}")
        assert Path(encrypted_file_path_actual).exists(), "Encrypted file was not created."

        # Decrypt
        decrypted_file_output_path = test_file_dir / "test_decrypted_module.txt"
        decrypted_path_actual = decrypt_file(encrypted_file_path_actual, test_password, str(decrypted_file_output_path))
        logger.info(f"Decryption complete. Decrypted file: {decrypted_path_actual}")
        assert Path(decrypted_path_actual).exists(), "Decrypted file was not created."


        with open(original_file_path, "r", encoding='utf-8') as f_orig, open(decrypted_path_actual, "r", encoding='utf-8') as f_dec:
            assert f_orig.read() == f_dec.read(), "Decrypted file content does not match original."
        logger.info(click.style("✅ File encryption/decryption test successful.", fg="green"))

    except Exception as e:
        logger.error(click.style(f"❌ File encryption/decryption test FAILED: {e}", fg="red"), exc_info=True)
    finally:
        # Clean up test files
        import shutil
        if test_file_dir.exists():
            shutil.rmtree(test_file_dir)
            logger.info(f"Cleaned up test directory: {test_file_dir}")
        pass
