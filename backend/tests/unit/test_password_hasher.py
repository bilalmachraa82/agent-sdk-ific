"""
Unit tests for PasswordHasher (Argon2id password hashing with bcrypt compatibility).

Tests cover:
- Argon2id hashing and verification
- bcrypt compatibility
- Automatic migration from bcrypt to Argon2id
- Algorithm detection
- Performance targets (<150ms)
- Error handling
- OWASP parameter validation
"""

import pytest
import asyncio
import time
from unittest.mock import patch

from backend.core.password_hasher import (
    PasswordHasher,
    get_password_hasher,
    PasswordHashError
)


@pytest.fixture
def hasher():
    """Create PasswordHasher instance."""
    return get_password_hasher(use_argon2=True)


@pytest.fixture
def bcrypt_hasher():
    """Create PasswordHasher with bcrypt for testing migration."""
    return get_password_hasher(use_argon2=False)


class TestArgon2idHashing:
    """Test Argon2id password hashing."""

    @pytest.mark.asyncio
    async def test_hash_password_creates_valid_hash(self, hasher):
        """Test that hash_password() creates valid Argon2id hash."""
        password = "TestPassword123!"
        hash_str = await hasher.hash_password(password)

        assert hash_str is not None
        assert isinstance(hash_str, str)
        assert hash_str.startswith("$argon2id$")

    @pytest.mark.asyncio
    async def test_hash_password_different_hashes(self, hasher):
        """Test that same password generates different hashes (salt)."""
        password = "TestPassword123!"
        hash1 = await hasher.hash_password(password)
        hash2 = await hasher.hash_password(password)

        assert hash1 != hash2  # Different salts

    @pytest.mark.asyncio
    async def test_verify_password_correct_password(self, hasher):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hash_str = await hasher.hash_password(password)

        is_valid = await hasher.verify_password(password, hash_str)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_password_incorrect_password(self, hasher):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hash_str = await hasher.hash_password(password)

        is_valid = await hasher.verify_password(wrong_password, hash_str)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_password_empty_password(self, hasher):
        """Test password verification with empty password."""
        password = "TestPassword123!"
        hash_str = await hasher.hash_password(password)

        is_valid = await hasher.verify_password("", hash_str)
        assert is_valid is False

    def test_hash_password_sync(self, hasher):
        """Test synchronous password hashing."""
        password = "TestPassword123!"
        hash_str = hasher.hash_password_sync(password)

        assert hash_str is not None
        assert hash_str.startswith("$argon2id$")

    def test_verify_password_sync(self, hasher):
        """Test synchronous password verification."""
        password = "TestPassword123!"
        hash_str = hasher.hash_password_sync(password)

        is_valid = hasher.verify_password_sync(password, hash_str)
        assert is_valid is True


class TestBcryptCompatibility:
    """Test backward compatibility with bcrypt hashes."""

    @pytest.mark.asyncio
    async def test_verify_bcrypt_hash(self, hasher, bcrypt_hasher):
        """Test that PasswordHasher can verify bcrypt hashes."""
        password = "TestPassword123!"
        bcrypt_hash = await bcrypt_hasher.hash_password(password)

        # Should be able to verify with Argon2id-enabled hasher
        is_valid = await hasher.verify_password(password, bcrypt_hash)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_and_rehash_bcrypt(self, hasher, bcrypt_hasher):
        """Test automatic migration from bcrypt to Argon2id."""
        password = "TestPassword123!"
        bcrypt_hash = await bcrypt_hasher.hash_password(password)

        # Verify and get new hash
        is_valid, new_hash = await hasher.verify_and_rehash(password, bcrypt_hash)

        assert is_valid is True
        assert new_hash is not None
        assert new_hash != bcrypt_hash
        assert new_hash.startswith("$argon2id$")

    @pytest.mark.asyncio
    async def test_verify_and_rehash_argon2id_no_rehash(self, hasher):
        """Test that Argon2id hashes don't get re-hashed."""
        password = "TestPassword123!"
        argon2_hash = await hasher.hash_password(password)

        # Should not re-hash if already Argon2id
        is_valid, new_hash = await hasher.verify_and_rehash(password, argon2_hash)

        assert is_valid is True
        assert new_hash is None  # No rehash needed

    @pytest.mark.asyncio
    async def test_verify_and_rehash_wrong_password(self, hasher, bcrypt_hasher):
        """Test that wrong password doesn't trigger rehash."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        bcrypt_hash = await bcrypt_hasher.hash_password(password)

        is_valid, new_hash = await hasher.verify_and_rehash(wrong_password, bcrypt_hash)

        assert is_valid is False
        assert new_hash is None


class TestAlgorithmDetection:
    """Test password hash algorithm detection."""

    def test_detect_argon2id(self, hasher):
        """Test detection of Argon2id hashes."""
        argon2_hash = hasher.hash_password_sync("password123")
        algo = hasher.detect_hash_algorithm(argon2_hash)

        assert algo == "argon2id"

    def test_detect_bcrypt(self, hasher, bcrypt_hasher):
        """Test detection of bcrypt hashes."""
        bcrypt_hash = bcrypt_hasher.hash_password_sync("password123")
        algo = hasher.detect_hash_algorithm(bcrypt_hash)

        assert algo == "bcrypt"

    def test_detect_unknown(self, hasher):
        """Test detection of unknown hash format."""
        unknown_hash = "$unknown$hash$format"
        algo = hasher.detect_hash_algorithm(unknown_hash)

        assert algo == "unknown"

    def test_detect_empty_hash(self, hasher):
        """Test detection with empty hash."""
        algo = hasher.detect_hash_algorithm("")
        assert algo == "unknown"


class TestRehashCheck:
    """Test needs_rehash() functionality."""

    def test_needs_rehash_bcrypt(self, hasher, bcrypt_hasher):
        """Test that bcrypt hashes need rehash."""
        bcrypt_hash = bcrypt_hasher.hash_password_sync("password123")
        needs_rehash = hasher.needs_rehash(bcrypt_hash)

        assert needs_rehash is True

    def test_needs_rehash_argon2id_false(self, hasher):
        """Test that Argon2id hashes don't need rehash."""
        argon2_hash = hasher.hash_password_sync("password123")
        needs_rehash = hasher.needs_rehash(argon2_hash)

        assert needs_rehash is False

    def test_needs_rehash_unknown_true(self, hasher):
        """Test that unknown hashes are flagged for rehash."""
        unknown_hash = "$unknown$hash$format"
        needs_rehash = hasher.needs_rehash(unknown_hash)

        assert needs_rehash is True


class TestPerformance:
    """Test performance targets (<150ms)."""

    @pytest.mark.asyncio
    async def test_hash_performance(self, hasher):
        """Test that hashing completes within 150ms."""
        password = "TestPassword123!"

        start = time.time()
        await hasher.hash_password(password)
        duration = (time.time() - start) * 1000  # Convert to ms

        assert duration < 150, f"Hash time {duration:.1f}ms exceeds 150ms target"

    @pytest.mark.asyncio
    async def test_verify_performance(self, hasher):
        """Test that verification completes within 150ms."""
        password = "TestPassword123!"
        hash_str = await hasher.hash_password(password)

        start = time.time()
        await hasher.verify_password(password, hash_str)
        duration = (time.time() - start) * 1000  # Convert to ms

        assert duration < 150, f"Verify time {duration:.1f}ms exceeds 150ms target"

    @pytest.mark.asyncio
    async def test_verify_and_rehash_performance(self, hasher, bcrypt_hasher):
        """Test that verification + rehash completes within 300ms."""
        password = "TestPassword123!"
        bcrypt_hash = await bcrypt_hasher.hash_password(password)

        start = time.time()
        await hasher.verify_and_rehash(password, bcrypt_hash)
        duration = (time.time() - start) * 1000  # Convert to ms

        # Verify + rehash should complete within 300ms
        assert duration < 300, f"Verify+rehash time {duration:.1f}ms exceeds 300ms target"


class TestOWASPParameters:
    """Test OWASP-recommended Argon2id parameters."""

    def test_time_cost_meets_owasp(self, hasher):
        """Test that time_cost >= 2 (OWASP recommendation)."""
        assert hasher._argon2.time_cost >= 2

    def test_memory_cost_meets_owasp(self, hasher):
        """Test that memory_cost >= 64 MiB (OWASP recommendation)."""
        # 64 MiB = 65536 KiB
        assert hasher._argon2.memory_cost >= 65536

    def test_parallelism_meets_owasp(self, hasher):
        """Test that parallelism >= 4 (OWASP recommendation)."""
        assert hasher._argon2.parallelism >= 4

    def test_hash_length_adequate(self, hasher):
        """Test that hash length >= 32 bytes (256 bits)."""
        assert hasher._argon2.hash_len >= 32

    def test_salt_length_adequate(self, hasher):
        """Test that salt length >= 16 bytes (128 bits)."""
        assert hasher._argon2.salt_len >= 16


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_hash_empty_password(self, hasher):
        """Test hashing empty password."""
        hash_str = await hasher.hash_password("")
        assert hash_str is not None
        assert hash_str.startswith("$argon2id$")

    @pytest.mark.asyncio
    async def test_hash_very_long_password(self, hasher):
        """Test hashing very long password (10KB)."""
        long_password = "a" * 10000
        hash_str = await hasher.hash_password(long_password)

        assert hash_str is not None
        is_valid = await hasher.verify_password(long_password, hash_str)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_hash_unicode_password(self, hasher):
        """Test hashing password with Unicode characters."""
        unicode_password = "пароль123!@#你好"
        hash_str = await hasher.hash_password(unicode_password)

        assert hash_str is not None
        is_valid = await hasher.verify_password(unicode_password, hash_str)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_corrupted_hash(self, hasher):
        """Test verification with corrupted hash."""
        password = "TestPassword123!"
        corrupted_hash = "$argon2id$v=19$m=65536$corrupted"

        is_valid = await hasher.verify_password(password, corrupted_hash)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_empty_hash(self, hasher):
        """Test verification with empty hash."""
        password = "TestPassword123!"
        is_valid = await hasher.verify_password(password, "")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_none_hash(self, hasher):
        """Test verification with None hash."""
        password = "TestPassword123!"

        with pytest.raises((TypeError, AttributeError)):
            await hasher.verify_password(password, None)


class TestConcurrency:
    """Test concurrent hashing and verification operations."""

    @pytest.mark.asyncio
    async def test_concurrent_hashing(self, hasher):
        """Test that concurrent hashing operations don't interfere."""
        passwords = [f"Password{i}!" for i in range(10)]

        # Hash all passwords concurrently
        tasks = [hasher.hash_password(pwd) for pwd in passwords]
        hashes = await asyncio.gather(*tasks)

        # All hashes should be unique
        assert len(hashes) == len(set(hashes))

        # Verify each password with its hash
        for password, hash_str in zip(passwords, hashes):
            is_valid = await hasher.verify_password(password, hash_str)
            assert is_valid is True

    @pytest.mark.asyncio
    async def test_concurrent_verification(self, hasher):
        """Test that concurrent verification operations are safe."""
        password = "TestPassword123!"
        hash_str = await hasher.hash_password(password)

        # Verify concurrently 50 times
        tasks = [hasher.verify_password(password, hash_str) for _ in range(50)]
        results = await asyncio.gather(*tasks)

        # All verifications should succeed
        assert all(results)

    @pytest.mark.asyncio
    async def test_concurrent_migration(self, hasher, bcrypt_hasher):
        """Test concurrent bcrypt → Argon2id migrations."""
        passwords = [f"Password{i}!" for i in range(5)]

        # Create bcrypt hashes
        bcrypt_hashes = [bcrypt_hasher.hash_password_sync(pwd) for pwd in passwords]

        # Migrate concurrently
        tasks = [
            hasher.verify_and_rehash(pwd, bcrypt_hash)
            for pwd, bcrypt_hash in zip(passwords, bcrypt_hashes)
        ]
        results = await asyncio.gather(*tasks)

        # All should succeed and provide new hashes
        for is_valid, new_hash in results:
            assert is_valid is True
            assert new_hash is not None
            assert new_hash.startswith("$argon2id$")


class TestGetPasswordHasher:
    """Test get_password_hasher() factory function."""

    def test_get_password_hasher_default(self):
        """Test that default returns Argon2id hasher."""
        hasher = get_password_hasher()
        assert hasher._use_argon2 is True

    def test_get_password_hasher_argon2(self):
        """Test explicitly requesting Argon2id."""
        hasher = get_password_hasher(use_argon2=True)
        assert hasher._use_argon2 is True

    def test_get_password_hasher_bcrypt(self):
        """Test explicitly requesting bcrypt."""
        hasher = get_password_hasher(use_argon2=False)
        assert hasher._use_argon2 is False

    def test_get_password_hasher_singleton(self):
        """Test that factory returns same instance."""
        hasher1 = get_password_hasher()
        hasher2 = get_password_hasher()

        # Should be same instance (singleton pattern)
        assert hasher1 is hasher2


@pytest.mark.integration
class TestPasswordHasherIntegration:
    """Integration tests for PasswordHasher with real database scenarios."""

    @pytest.mark.asyncio
    async def test_user_registration_flow(self, hasher):
        """Test complete user registration flow."""
        # User provides password during registration
        plain_password = "MySecurePassword123!"

        # Hash password for storage
        hash_str = await hasher.hash_password(plain_password)

        # Store hash_str in database (simulated)
        stored_hash = hash_str

        # User later logs in with same password
        login_password = "MySecurePassword123!"
        is_valid = await hasher.verify_password(login_password, stored_hash)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_user_login_with_bcrypt_migration(self, hasher, bcrypt_hasher):
        """Test user login triggering bcrypt → Argon2id migration."""
        # Old user has bcrypt hash in database
        plain_password = "OldPassword123!"
        bcrypt_hash = await bcrypt_hasher.hash_password(plain_password)

        # Store bcrypt hash (simulated)
        stored_hash = bcrypt_hash

        # User logs in - triggers migration
        is_valid, new_hash = await hasher.verify_and_rehash(plain_password, stored_hash)

        assert is_valid is True
        assert new_hash is not None

        # Update database with new hash (simulated)
        stored_hash = new_hash

        # Next login uses Argon2id
        is_valid, new_hash = await hasher.verify_and_rehash(plain_password, stored_hash)

        assert is_valid is True
        assert new_hash is None  # No migration needed

    @pytest.mark.asyncio
    async def test_password_change_flow(self, hasher):
        """Test password change flow."""
        # User's current password
        old_password = "OldPassword123!"
        old_hash = await hasher.hash_password(old_password)

        # User changes password
        new_password = "NewPassword456!"
        new_hash = await hasher.hash_password(new_password)

        # Old password should no longer work
        is_valid = await hasher.verify_password(old_password, new_hash)
        assert is_valid is False

        # New password should work
        is_valid = await hasher.verify_password(new_password, new_hash)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_failed_login_attempts(self, hasher):
        """Test multiple failed login attempts."""
        password = "CorrectPassword123!"
        hash_str = await hasher.hash_password(password)

        # Simulate 5 failed login attempts
        failed_attempts = [
            "WrongPassword1!",
            "WrongPassword2!",
            "WrongPassword3!",
            "WrongPassword4!",
            "WrongPassword5!"
        ]

        for wrong_password in failed_attempts:
            is_valid = await hasher.verify_password(wrong_password, hash_str)
            assert is_valid is False

        # Correct password should still work
        is_valid = await hasher.verify_password(password, hash_str)
        assert is_valid is True


class TestSecurityProperties:
    """Test security properties of password hashing."""

    def test_hash_contains_no_plaintext(self, hasher):
        """Test that hash doesn't contain plaintext password."""
        password = "SecretPassword123!"
        hash_str = hasher.hash_password_sync(password)

        assert password not in hash_str
        assert password.lower() not in hash_str.lower()

    def test_hash_contains_salt(self, hasher):
        """Test that hash contains salt (different hashes for same password)."""
        password = "TestPassword123!"
        hash1 = hasher.hash_password_sync(password)
        hash2 = hasher.hash_password_sync(password)

        # Hashes should differ (salt randomization)
        assert hash1 != hash2

    def test_hash_deterministic_with_same_salt(self, hasher):
        """Test that hash is deterministic with same salt."""
        password = "TestPassword123!"
        hash1 = hasher.hash_password_sync(password)

        # Verify with same hash multiple times
        result1 = hasher.verify_password_sync(password, hash1)
        result2 = hasher.verify_password_sync(password, hash1)
        result3 = hasher.verify_password_sync(password, hash1)

        assert result1 == result2 == result3 == True

    @pytest.mark.asyncio
    async def test_timing_attack_resistance(self, hasher):
        """Test that verification time is constant (timing attack resistance)."""
        password = "TestPassword123!"
        hash_str = await hasher.hash_password(password)

        # Measure time for correct password
        start = time.time()
        await hasher.verify_password(password, hash_str)
        time_correct = time.time() - start

        # Measure time for wrong password
        start = time.time()
        await hasher.verify_password("WrongPassword!", hash_str)
        time_wrong = time.time() - start

        # Times should be similar (within 20ms)
        diff = abs(time_correct - time_wrong) * 1000
        assert diff < 20, f"Timing difference {diff:.1f}ms may leak information"
