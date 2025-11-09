"""
RSA Key Management for RS256 JWT signing
Handles key generation, rotation, and JWKS export
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import structlog

from backend.core.config import settings

logger = structlog.get_logger(__name__)


class KeyManager:
    """
    Manages RSA key pairs for JWT signing with automatic rotation.

    Features:
    - RSA-4096 key pair generation
    - KID (Key ID) based identification
    - 30-day rotation cycle
    - JWKS endpoint support
    - Multiple active keys during rotation period
    """

    # Key rotation period
    KEY_ROTATION_DAYS = 30
    KEY_GRACE_PERIOD_DAYS = 7  # Keep old keys valid for 7 days after rotation

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize KeyManager.

        Args:
            storage_path: Path to store keys (defaults to backend/.keys/)
        """
        self.storage_path = storage_path or Path(__file__).parent.parent / ".keys"
        self.storage_path.mkdir(exist_ok=True, mode=0o700)  # rwx------

        self._keys: Dict[str, Dict] = {}
        self._load_keys()

    def generate_key_pair(self, kid: Optional[str] = None) -> Tuple[str, bytes, bytes]:
        """
        Generate a new RSA-4096 key pair.

        Args:
            kid: Optional Key ID. If not provided, generates a random one.

        Returns:
            Tuple of (kid, private_key_pem, public_key_pem)
        """
        if kid is None:
            kid = self._generate_kid()

        logger.info("Generating new RSA-4096 key pair", kid=kid)

        # Generate RSA-4096 key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )

        # Serialize private key (encrypted with password)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                settings.jwt_secret_key.encode()
            )
        )

        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        logger.info("RSA key pair generated successfully", kid=kid)

        return kid, private_pem, public_pem

    def create_key(self, kid: Optional[str] = None) -> str:
        """
        Create and store a new key pair.

        Args:
            kid: Optional Key ID

        Returns:
            The KID of the newly created key
        """
        kid, private_pem, public_pem = self.generate_key_pair(kid)

        # Store key metadata
        key_data = {
            "kid": kid,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=self.KEY_ROTATION_DAYS)).isoformat(),
            "algorithm": "RS256",
            "status": "active",
            "private_key": private_pem.decode('utf-8'),
            "public_key": public_pem.decode('utf-8')
        }

        self._keys[kid] = key_data
        self._save_key(kid, key_data)

        logger.info("New key created and stored", kid=kid, expires_at=key_data["expires_at"])

        return kid

    def get_current_signing_key(self) -> Optional[Dict]:
        """
        Get the current active signing key.

        Returns:
            Key data dict or None if no active key exists
        """
        active_keys = [
            k for k in self._keys.values()
            if k["status"] == "active" and datetime.fromisoformat(k["expires_at"]) > datetime.utcnow()
        ]

        if not active_keys:
            logger.warning("No active signing key found, creating new key")
            kid = self.create_key()
            return self._keys[kid]

        # Return the most recently created key
        return max(active_keys, key=lambda k: k["created_at"])

    def get_key(self, kid: str) -> Optional[Dict]:
        """
        Get a specific key by KID.

        Args:
            kid: Key ID

        Returns:
            Key data dict or None if not found
        """
        return self._keys.get(kid)

    def get_public_keys(self) -> List[Dict]:
        """
        Get all active public keys for JWKS endpoint.

        Returns:
            List of public key data in JWK format
        """
        now = datetime.utcnow()
        grace_period = timedelta(days=self.KEY_GRACE_PERIOD_DAYS)

        # Include keys that are active or within grace period
        valid_keys = [
            k for k in self._keys.values()
            if (
                k["status"] == "active" and
                datetime.fromisoformat(k["expires_at"]) + grace_period > now
            )
        ]

        jwks = []
        for key_data in valid_keys:
            jwk = self._public_key_to_jwk(key_data)
            jwks.append(jwk)

        return jwks

    def rotate_keys(self) -> str:
        """
        Rotate keys: create new key and mark old keys as rotated.

        Returns:
            KID of the new key
        """
        logger.info("Starting key rotation")

        # Create new key
        new_kid = self.create_key()

        # Mark old active keys as rotated (but keep them valid for grace period)
        now = datetime.utcnow()
        for kid, key_data in self._keys.items():
            if kid != new_kid and key_data["status"] == "active":
                expires_at = datetime.fromisoformat(key_data["expires_at"])
                if expires_at < now:
                    key_data["status"] = "expired"
                    logger.info("Marked key as expired", kid=kid)
                else:
                    key_data["status"] = "rotated"
                    logger.info("Marked key as rotated", kid=kid)

                self._save_key(kid, key_data)

        logger.info("Key rotation completed", new_kid=new_kid)

        return new_kid

    def cleanup_expired_keys(self) -> int:
        """
        Remove expired keys that are past grace period.

        Returns:
            Number of keys removed
        """
        now = datetime.utcnow()
        grace_period = timedelta(days=self.KEY_GRACE_PERIOD_DAYS)

        to_remove = []
        for kid, key_data in self._keys.items():
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if expires_at + grace_period < now:
                to_remove.append(kid)

        for kid in to_remove:
            self._delete_key(kid)
            del self._keys[kid]
            logger.info("Removed expired key", kid=kid)

        return len(to_remove)

    def _generate_kid(self) -> str:
        """
        Generate a unique Key ID.

        Returns:
            A random KID string
        """
        return f"key_{secrets.token_urlsafe(16)}"

    def _public_key_to_jwk(self, key_data: Dict) -> Dict:
        """
        Convert public key PEM to JWK format.

        Args:
            key_data: Key data dict

        Returns:
            JWK representation
        """
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import base64

        # Load public key
        public_key_pem = key_data["public_key"].encode('utf-8')
        public_key = serialization.load_pem_public_key(
            public_key_pem,
            backend=default_backend()
        )

        # Extract RSA public numbers
        public_numbers = public_key.public_numbers()

        # Convert to base64url encoding
        def int_to_base64url(num: int) -> str:
            # Convert int to bytes
            num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
            # Base64url encode
            return base64.urlsafe_b64encode(num_bytes).decode('utf-8').rstrip('=')

        n = int_to_base64url(public_numbers.n)
        e = int_to_base64url(public_numbers.e)

        return {
            "kty": "RSA",
            "use": "sig",
            "kid": key_data["kid"],
            "alg": "RS256",
            "n": n,
            "e": e
        }

    def _load_keys(self):
        """Load all keys from storage."""
        if not self.storage_path.exists():
            logger.info("No key storage found, will create on first key generation")
            return

        for key_file in self.storage_path.glob("*.json"):
            try:
                with open(key_file, 'r') as f:
                    key_data = json.load(f)
                    self._keys[key_data["kid"]] = key_data
                    logger.info("Loaded key from storage", kid=key_data["kid"])
            except Exception as e:
                logger.error("Failed to load key file", file=str(key_file), error=str(e))

    def _save_key(self, kid: str, key_data: Dict):
        """
        Save key to storage.

        Args:
            kid: Key ID
            key_data: Key data dict
        """
        key_file = self.storage_path / f"{kid}.json"
        try:
            with open(key_file, 'w') as f:
                json.dump(key_data, f, indent=2)
            # Secure file permissions
            key_file.chmod(0o600)  # rw-------
            logger.debug("Key saved to storage", kid=kid)
        except Exception as e:
            logger.error("Failed to save key", kid=kid, error=str(e))
            raise

    def _delete_key(self, kid: str):
        """
        Delete key from storage.

        Args:
            kid: Key ID
        """
        key_file = self.storage_path / f"{kid}.json"
        try:
            if key_file.exists():
                key_file.unlink()
                logger.debug("Key deleted from storage", kid=kid)
        except Exception as e:
            logger.error("Failed to delete key", kid=kid, error=str(e))

    def get_private_key_for_signing(self, kid: Optional[str] = None) -> Tuple[str, bytes]:
        """
        Get private key for JWT signing.

        Args:
            kid: Optional Key ID. If not provided, uses current signing key.

        Returns:
            Tuple of (kid, private_key_bytes)
        """
        if kid is None:
            key_data = self.get_current_signing_key()
        else:
            key_data = self.get_key(kid)

        if not key_data:
            raise ValueError(f"Key not found: {kid}")

        private_key_pem = key_data["private_key"].encode('utf-8')

        # Load private key with password
        from cryptography.hazmat.primitives import serialization
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=settings.jwt_secret_key.encode(),
            backend=default_backend()
        )

        return key_data["kid"], private_key

    def get_public_key_for_verification(self, kid: str) -> bytes:
        """
        Get public key for JWT verification.

        Args:
            kid: Key ID from JWT header

        Returns:
            Public key bytes
        """
        key_data = self.get_key(kid)
        if not key_data:
            raise ValueError(f"Key not found: {kid}")

        return key_data["public_key"].encode('utf-8')


# Global KeyManager instance
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """
    Get or create the global KeyManager instance.

    Returns:
        KeyManager instance
    """
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
        logger.info("KeyManager initialized")
    return _key_manager
