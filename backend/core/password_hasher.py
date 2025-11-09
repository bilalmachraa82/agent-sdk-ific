"""
Argon2id password hashing with backward compatibility for bcrypt.

Implements memory-hard password hashing following OWASP 2025 recommendations.
Performance target: <150ms per hash.
"""

import asyncio
import bcrypt
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Literal
import structlog
from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash

logger = structlog.get_logger(__name__)

# Global thread pool for CPU-bound operations
_password_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="password-")

# Argon2id configuration following OWASP recommendations
# These parameters provide good security with <150ms performance
_argon2_hasher = Argon2PasswordHasher(
    time_cost=2,          # Number of iterations
    memory_cost=65536,    # 64 MiB memory usage
    parallelism=4,        # Number of parallel threads
    hash_len=32,          # Hash output length in bytes
    salt_len=16,          # Salt length in bytes
    encoding='utf-8'
)


class PasswordHasher:
    """
    Password hasher supporting both Argon2id (modern) and bcrypt (legacy).

    Features:
    - Argon2id hashing with OWASP-recommended parameters
    - Automatic hash algorithm detection
    - Backward compatibility with existing bcrypt hashes
    - Async/await support for non-blocking operations
    - Performance: <150ms per hash
    """

    def __init__(self, use_argon2: bool = True):
        """
        Initialize password hasher.

        Args:
            use_argon2: If True, use Argon2id for new hashes (default).
                       If False, use bcrypt for backward compatibility.
        """
        self.use_argon2 = use_argon2
        self._argon2 = _argon2_hasher

        if use_argon2:
            logger.info("Argon2id password hashing enabled")
        else:
            logger.info("Bcrypt password hashing enabled (legacy mode)")

    def detect_hash_algorithm(self, password_hash: str) -> Literal["argon2id", "bcrypt", "unknown"]:
        """
        Detect which algorithm was used to create a password hash.

        Args:
            password_hash: The password hash string

        Returns:
            "argon2id", "bcrypt", or "unknown"
        """
        if password_hash.startswith("$argon2id$"):
            return "argon2id"
        elif password_hash.startswith("$2b$") or password_hash.startswith("$2a$"):
            return "bcrypt"
        else:
            return "unknown"

    def hash_password_sync(self, password: str) -> str:
        """
        Hash a password synchronously.

        WARNING: This blocks the event loop. Use async_hash_password() instead.

        Args:
            password: Plain text password

        Returns:
            Password hash string
        """
        if self.use_argon2:
            return self._argon2.hash(password)
        else:
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(password_bytes, salt)
            return hashed.decode('utf-8')

    async def async_hash_password(self, password: str) -> str:
        """
        Hash a password asynchronously (non-blocking).

        This is the RECOMMENDED method for async contexts.
        Offloads CPU-bound operation to thread pool.

        Args:
            password: Plain text password

        Returns:
            Password hash string
        """
        loop = asyncio.get_event_loop()

        def _hash():
            if self.use_argon2:
                return self._argon2.hash(password)
            else:
                password_bytes = password.encode('utf-8')
                salt = bcrypt.gensalt(rounds=12)
                hashed = bcrypt.hashpw(password_bytes, salt)
                return hashed.decode('utf-8')

        return await loop.run_in_executor(_password_executor, _hash)

    def verify_password_sync(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash synchronously.

        Automatically detects hash algorithm (Argon2id or bcrypt).

        WARNING: This blocks the event loop. Use async_verify_password() instead.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Password hash to verify against

        Returns:
            True if password matches, False otherwise
        """
        algorithm = self.detect_hash_algorithm(hashed_password)

        try:
            if algorithm == "argon2id":
                # Verify with Argon2id
                self._argon2.verify(hashed_password, plain_password)
                return True

            elif algorithm == "bcrypt":
                # Verify with bcrypt
                password_bytes = plain_password.encode('utf-8')
                hashed_bytes = hashed_password.encode('utf-8')
                return bcrypt.checkpw(password_bytes, hashed_bytes)

            else:
                logger.error("Unknown hash algorithm", hash_prefix=hashed_password[:20])
                return False

        except (VerifyMismatchError, VerificationError, InvalidHash):
            # Argon2 verification failed
            return False
        except Exception as e:
            logger.error("Password verification error", error=str(e))
            return False

    async def async_verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash asynchronously (non-blocking).

        Automatically detects hash algorithm (Argon2id or bcrypt).

        This is the RECOMMENDED method for async contexts.
        Offloads CPU-bound operation to thread pool.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Password hash to verify against

        Returns:
            True if password matches, False otherwise
        """
        loop = asyncio.get_event_loop()

        def _verify():
            return self.verify_password_sync(plain_password, hashed_password)

        return await loop.run_in_executor(_password_executor, _verify)

    def needs_rehash(self, password_hash: str) -> bool:
        """
        Check if a password hash needs to be rehashed.

        Returns True if:
        - Hash uses bcrypt and Argon2id is enabled
        - Hash uses outdated Argon2 parameters

        Args:
            password_hash: Password hash to check

        Returns:
            True if hash should be regenerated
        """
        algorithm = self.detect_hash_algorithm(password_hash)

        # If using Argon2id and hash is bcrypt, needs rehash
        if self.use_argon2 and algorithm == "bcrypt":
            return True

        # Check if Argon2id hash needs rehashing (outdated parameters)
        if algorithm == "argon2id":
            try:
                return self._argon2.check_needs_rehash(password_hash)
            except Exception:
                return True

        return False

    async def verify_and_rehash(
        self,
        plain_password: str,
        hashed_password: str
    ) -> Tuple[bool, str | None]:
        """
        Verify password and rehash if needed.

        This is useful during login to automatically upgrade old bcrypt hashes
        to Argon2id without user intervention.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Current password hash

        Returns:
            Tuple of (is_valid, new_hash_or_none)
            - is_valid: True if password matches
            - new_hash_or_none: New hash if rehashing was needed, None otherwise
        """
        # First verify the password
        is_valid = await self.async_verify_password(plain_password, hashed_password)

        if not is_valid:
            return False, None

        # If valid, check if rehash is needed
        if self.needs_rehash(hashed_password):
            logger.info("Rehashing password with Argon2id", old_algorithm=self.detect_hash_algorithm(hashed_password))
            new_hash = await self.async_hash_password(plain_password)
            return True, new_hash

        return True, None


# Global password hasher instance
_password_hasher: PasswordHasher | None = None


def get_password_hasher(use_argon2: bool = True) -> PasswordHasher:
    """
    Get or create the global PasswordHasher instance.

    Args:
        use_argon2: If True, use Argon2id for new hashes

    Returns:
        PasswordHasher instance
    """
    global _password_hasher
    if _password_hasher is None:
        _password_hasher = PasswordHasher(use_argon2=use_argon2)
        logger.info("PasswordHasher initialized", use_argon2=use_argon2)
    return _password_hasher


# Convenience functions for easy usage
async def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id (async).

    Args:
        password: Plain text password

    Returns:
        Password hash string
    """
    hasher = get_password_hasher(use_argon2=True)
    return await hasher.async_hash_password(password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash (async).

    Automatically detects hash algorithm (Argon2id or bcrypt).

    Args:
        plain_password: Plain text password
        hashed_password: Password hash

    Returns:
        True if password matches
    """
    hasher = get_password_hasher()
    return await hasher.async_verify_password(plain_password, hashed_password)


async def verify_and_rehash(
    plain_password: str,
    hashed_password: str
) -> Tuple[bool, str | None]:
    """
    Verify password and rehash if needed (async).

    Args:
        plain_password: Plain text password
        hashed_password: Current password hash

    Returns:
        Tuple of (is_valid, new_hash_or_none)
    """
    hasher = get_password_hasher(use_argon2=True)
    return await hasher.verify_and_rehash(plain_password, hashed_password)
