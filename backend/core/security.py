"""
Security module for JWT authentication, password hashing, and tenant context management.
Implements secure token generation with tenant isolation.

Supports both HS256 (legacy) and RS256 (modern) JWT signing with automatic migration.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import structlog

from .config import settings

logger = structlog.get_logger(__name__)

# Global thread pool for CPU-bound bcrypt operations
_bcrypt_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bcrypt-")


class SecurityManager:
    """
    Manages authentication, authorization, and encryption.

    Supports both HS256 (legacy) and RS256 (modern) JWT signing.
    Set USE_RS256 environment variable to enable RS256.
    """

    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_expiration_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_expiration_days

        # RS256 support flag (can be set via environment variable)
        self.use_rs256 = getattr(settings, 'use_rs256_jwt', False)

        # Lazy-load KeyManager only if RS256 is enabled
        self._key_manager = None

        if self.use_rs256:
            logger.info("RS256 JWT signing enabled")

    @property
    def key_manager(self):
        """Lazy-load KeyManager when needed."""
        if self._key_manager is None and self.use_rs256:
            from .key_manager import get_key_manager
            self._key_manager = get_key_manager()
        return self._key_manager

    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password using bcrypt (synchronous).

        WARNING: This is a synchronous blocking operation (~50-80ms).
        Use async_hash_password() in async contexts to avoid blocking the event loop.
        """
        # Convert password to bytes and hash with bcrypt
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    async def async_hash_password(self, password: str) -> str:
        """
        Hash a plain text password using bcrypt (async, non-blocking).

        Offloads CPU-bound bcrypt operation to thread pool to avoid blocking
        the asyncio event loop. This is the RECOMMENDED method for async contexts.

        Performance: ~50-80ms in thread pool vs blocking event loop.
        """
        loop = asyncio.get_event_loop()

        def _hash():
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(password_bytes, salt)
            return hashed.decode('utf-8')

        return await loop.run_in_executor(_bcrypt_executor, _hash)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its bcrypt hash (synchronous).

        WARNING: This is a synchronous blocking operation (~50-80ms).
        Use async_verify_password() in async contexts to avoid blocking the event loop.
        """
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    async def async_verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its bcrypt hash (async, non-blocking).

        Offloads CPU-bound bcrypt operation to thread pool to avoid blocking
        the asyncio event loop. This is the RECOMMENDED method for async contexts.

        Performance: ~50-80ms in thread pool vs blocking event loop.
        """
        loop = asyncio.get_event_loop()

        def _verify():
            password_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)

        return await loop.run_in_executor(_bcrypt_executor, _verify)

    def create_access_token(
        self,
        data: Dict[str, Any],
        tenant_id: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create JWT access token with tenant context.

        Supports both HS256 (legacy) and RS256 (modern) algorithms.
        RS256 tokens include 'kid' in header for key rotation support.

        Args:
            data: Token payload data
            tenant_id: Tenant UUID for isolation
            expires_delta: Optional custom expiration

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        # Add tenant context to token
        to_encode.update({"tenant_id": tenant_id})

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        # Use RS256 if enabled, otherwise fallback to HS256
        if self.use_rs256 and self.key_manager:
            return self._create_rs256_token(to_encode)
        else:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm="HS256")
            return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any], tenant_id: str) -> str:
        """
        Create JWT refresh token with extended expiration.

        Supports both HS256 (legacy) and RS256 (modern) algorithms.
        """
        to_encode = data.copy()
        to_encode.update({"tenant_id": tenant_id})

        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })

        # Use RS256 if enabled, otherwise fallback to HS256
        if self.use_rs256 and self.key_manager:
            return self._create_rs256_token(to_encode)
        else:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm="HS256")
            return encoded_jwt

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token.

        Supports both HS256 (legacy) and RS256 (modern) algorithms.
        Automatically detects algorithm from token header.

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # Peek at token header to determine algorithm
            unverified_header = jwt.get_unverified_header(token)
            algorithm = unverified_header.get("alg", "HS256")

            if algorithm == "RS256":
                # RS256 token - use public key verification
                kid = unverified_header.get("kid")
                if not kid:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="RS256 token missing 'kid' in header",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                if not self.key_manager:
                    from .key_manager import get_key_manager
                    self._key_manager = get_key_manager()

                # Get public key for this kid
                public_key_pem = self.key_manager.get_public_key_for_verification(kid)

                # Decode with RS256
                payload = jwt.decode(
                    token,
                    public_key_pem,
                    algorithms=["RS256"],
                    options={"verify_signature": True}
                )
                return payload

            elif algorithm == "HS256":
                # HS256 token - use secret key
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=["HS256"]
                )
                return payload

            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Unsupported algorithm: {algorithm}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _create_rs256_token(self, payload: Dict[str, Any]) -> str:
        """
        Create RS256-signed JWT token.

        Args:
            payload: Token payload data

        Returns:
            Encoded JWT token string with RS256 signature
        """
        # Get current signing key
        kid, private_key = self.key_manager.get_private_key_for_signing()

        # Serialize private key for jose library
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Create JWT with kid in header
        encoded_jwt = jwt.encode(
            payload,
            private_key_pem,
            algorithm="RS256",
            headers={"kid": kid}
        )

        logger.debug("Created RS256 token", kid=kid)

        return encoded_jwt

    def get_tenant_from_token(self, token: str) -> str:
        """Extract tenant ID from JWT token."""
        payload = self.decode_token(token)
        tenant_id = payload.get("tenant_id")

        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing tenant context",
            )

        return tenant_id


# Global security manager instance
security = SecurityManager()


# Convenience functions for backward compatibility
def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt (synchronous).

    WARNING: Blocks event loop ~50-80ms. Use async_get_password_hash() instead.
    """
    return security.hash_password(password)


async def async_get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt (async, non-blocking).

    RECOMMENDED for all async contexts. Offloads to thread pool.
    """
    return await security.async_hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash (synchronous).

    WARNING: Blocks event loop ~50-80ms. Use async_verify_password() instead.
    """
    return security.verify_password(plain_password, hashed_password)


async def async_verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash (async, non-blocking).

    RECOMMENDED for all async contexts. Offloads to thread pool.
    """
    return await security.async_verify_password(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], tenant_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    return security.create_access_token(data, tenant_id, expires_delta)


def create_refresh_token(data: Dict[str, Any], tenant_id: str) -> str:
    """Create JWT refresh token."""
    return security.create_refresh_token(data, tenant_id)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token."""
    return security.decode_token(token)


def get_tenant_from_token(token: str) -> str:
    """Extract tenant ID from JWT token."""
    return security.get_tenant_from_token(token)
