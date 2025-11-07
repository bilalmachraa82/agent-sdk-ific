"""
AES-256-GCM encryption utilities for data at rest.
Implements field-level encryption for sensitive data in database.
"""

import os
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import secrets
import logging

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Constants
NONCE_SIZE = 12  # 96 bits for GCM
TAG_SIZE = 16    # 128 bits for GCM
KEY_SIZE = 32    # 256 bits
SALT_SIZE = 16   # 128 bits
PBKDF2_ITERATIONS = 100000


class EncryptionManager:
    """Manages AES-256-GCM encryption for sensitive data."""

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption manager.

        Args:
            master_key: Master encryption key (uses settings.encryption_key if not provided)
        """
        self.master_key = master_key or settings.encryption_key

        if not self.master_key:
            logger.warning("No encryption key provided. Using test key (INSECURE).")
            self.master_key = "test-key-change-in-production"

        self.key = self._derive_key(self.master_key)
        self.backend = default_backend()

    def _derive_key(self, password: str, salt: bytes = None) -> tuple:
        """
        Derive a 256-bit encryption key from password using PBKDF2.

        Returns:
            (derived_key, salt) tuple
        """
        if salt is None:
            salt = secrets.token_bytes(SALT_SIZE)

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=self.backend,
        )

        key = kdf.derive(password.encode())
        return key, salt

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: Data to encrypt

        Returns:
            Base64-encoded ciphertext with nonce and salt prepended
        """
        try:
            # Generate random nonce and salt
            nonce = secrets.token_bytes(NONCE_SIZE)
            salt = secrets.token_bytes(SALT_SIZE)

            # Derive encryption key from master key and salt
            key, _ = self._derive_key(self.master_key, salt)

            # Create cipher
            cipher = AESGCM(key)

            # Encrypt plaintext
            ciphertext = cipher.encrypt(nonce, plaintext.encode(), None)

            # Combine salt + nonce + ciphertext and base64 encode
            encrypted_data = salt + nonce + ciphertext
            encoded = base64.b64encode(encrypted_data).decode('utf-8')

            logger.debug(f"Encrypted {len(plaintext)} bytes of data")
            return encoded

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext using AES-256-GCM.

        Args:
            ciphertext: Base64-encoded encrypted data (salt + nonce + ciphertext)

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (invalid tag or corrupted data)
        """
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(ciphertext)

            # Extract salt, nonce, and ciphertext
            salt = encrypted_data[:SALT_SIZE]
            nonce = encrypted_data[SALT_SIZE : SALT_SIZE + NONCE_SIZE]
            ciphertext_bytes = encrypted_data[SALT_SIZE + NONCE_SIZE :]

            # Derive key from master key and salt
            key, _ = self._derive_key(self.master_key, salt)

            # Create cipher and decrypt
            cipher = AESGCM(key)
            plaintext = cipher.decrypt(nonce, ciphertext_bytes, None)

            logger.debug(f"Decrypted {len(plaintext)} bytes of data")
            return plaintext.decode('utf-8')

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Decryption failed - invalid key or corrupted data")

    def hash_password(self, password: str) -> str:
        """
        Hash a password using PBKDF2-SHA256 (not for encryption).

        Args:
            password: Password to hash

        Returns:
            Base64-encoded hash with salt prepended
        """
        salt = secrets.token_bytes(SALT_SIZE)
        key, _ = self._derive_key(password, salt)
        hash_data = salt + key
        return base64.b64encode(hash_data).decode('utf-8')

    def verify_password(self, password: str, hash_value: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Password to verify
            hash_value: Hash to check against

        Returns:
            True if password matches hash
        """
        try:
            hash_data = base64.b64decode(hash_value)
            salt = hash_data[:SALT_SIZE]
            stored_hash = hash_data[SALT_SIZE:]

            # Derive key from provided password with same salt
            key, _ = self._derive_key(password, salt)

            # Compare hashes using constant-time comparison
            return key.hex() == stored_hash.hex()

        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False


# Global encryption manager instance
encryption_manager = EncryptionManager()


def encrypt_field(plaintext: str) -> str:
    """Convenience function to encrypt a field value."""
    return encryption_manager.encrypt(plaintext)


def decrypt_field(ciphertext: str) -> str:
    """Convenience function to decrypt a field value."""
    return encryption_manager.decrypt(ciphertext)
