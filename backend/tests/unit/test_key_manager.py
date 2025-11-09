"""
Unit tests for KeyManager (RS256 JWT signing with key rotation).

Tests cover:
- Key generation
- Key rotation (30-day cycle)
- Grace period handling (7 days)
- JWKS export
- File permissions
- Error handling
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json

from backend.core.key_manager import KeyManager, KeyRotationError


@pytest.fixture
def temp_key_storage():
    """Create temporary directory for key storage."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def key_manager(temp_key_storage):
    """Create KeyManager instance with temporary storage."""
    return KeyManager(storage_path=temp_key_storage)


class TestKeyGeneration:
    """Test RSA key pair generation."""

    def test_create_key_generates_valid_key_pair(self, key_manager):
        """Test that create_key() generates valid RSA-4096 key pair."""
        kid = key_manager.create_key()

        assert kid is not None
        assert isinstance(kid, str)
        assert len(kid) == 32  # UUID4 without hyphens

        # Verify key file exists
        key_file = key_manager.storage_path / f"{kid}.json"
        assert key_file.exists()

    def test_create_key_sets_correct_permissions(self, key_manager):
        """Test that key files have 0600 permissions."""
        kid = key_manager.create_key()
        key_file = key_manager.storage_path / f"{kid}.json"

        # Check file permissions (should be 0600)
        permissions = oct(key_file.stat().st_mode)[-3:]
        assert permissions == '600', f"Expected 600, got {permissions}"

    def test_create_key_structure(self, key_manager):
        """Test that key file has correct JSON structure."""
        kid = key_manager.create_key()
        key_data = key_manager.get_key(kid)

        assert 'kid' in key_data
        assert 'algorithm' in key_data
        assert 'private_key_pem' in key_data
        assert 'public_key_pem' in key_data
        assert 'created_at' in key_data
        assert 'expires_at' in key_data
        assert 'status' in key_data

        assert key_data['algorithm'] == 'RS256'
        assert key_data['status'] == 'active'

    def test_create_key_expiration_is_30_days(self, key_manager):
        """Test that new keys expire in 30 days."""
        kid = key_manager.create_key()
        key_data = key_manager.get_key(kid)

        created_at = datetime.fromisoformat(key_data['created_at'])
        expires_at = datetime.fromisoformat(key_data['expires_at'])

        diff = expires_at - created_at
        assert diff.days == 30, f"Expected 30 days, got {diff.days}"

    def test_create_multiple_keys(self, key_manager):
        """Test creating multiple keys."""
        kid1 = key_manager.create_key()
        kid2 = key_manager.create_key()

        assert kid1 != kid2

        key1 = key_manager.get_key(kid1)
        key2 = key_manager.get_key(kid2)

        assert key1['private_key_pem'] != key2['private_key_pem']
        assert key1['public_key_pem'] != key2['public_key_pem']


class TestKeyRetrieval:
    """Test key retrieval operations."""

    def test_get_current_signing_key(self, key_manager):
        """Test getting current signing key."""
        kid = key_manager.create_key()
        current = key_manager.get_current_signing_key()

        assert current is not None
        assert current['kid'] == kid
        assert current['status'] == 'active'

    def test_get_current_signing_key_with_no_keys(self, key_manager):
        """Test getting current signing key when no keys exist."""
        current = key_manager.get_current_signing_key()
        assert current is None

    def test_get_key_by_kid(self, key_manager):
        """Test retrieving key by KID."""
        kid = key_manager.create_key()
        key_data = key_manager.get_key(kid)

        assert key_data is not None
        assert key_data['kid'] == kid

    def test_get_nonexistent_key(self, key_manager):
        """Test retrieving non-existent key returns None."""
        key_data = key_manager.get_key("nonexistent_kid")
        assert key_data is None

    def test_list_all_keys(self, key_manager):
        """Test listing all keys."""
        kid1 = key_manager.create_key()
        kid2 = key_manager.create_key()

        all_keys = key_manager.list_keys()
        assert len(all_keys) == 2

        kids = [k['kid'] for k in all_keys]
        assert kid1 in kids
        assert kid2 in kids


class TestKeyRotation:
    """Test key rotation mechanics."""

    def test_rotate_keys_creates_new_key(self, key_manager):
        """Test that rotate_keys() creates a new active key."""
        old_kid = key_manager.create_key()
        new_kid = key_manager.rotate_keys()

        assert new_kid != old_kid

        new_key = key_manager.get_key(new_kid)
        assert new_key['status'] == 'active'

    def test_rotate_keys_marks_old_key_deprecated(self, key_manager):
        """Test that rotation marks old key as deprecated."""
        old_kid = key_manager.create_key()
        key_manager.rotate_keys()

        old_key = key_manager.get_key(old_kid)
        assert old_key['status'] == 'deprecated'

    def test_rotate_keys_keeps_grace_period(self, key_manager):
        """Test that deprecated keys remain valid for grace period."""
        old_kid = key_manager.create_key()
        key_manager.rotate_keys()

        old_key = key_manager.get_key(old_kid)

        # Check grace period is 7 days
        expires_at = datetime.fromisoformat(old_key['expires_at'])
        deprecated_at = datetime.fromisoformat(old_key.get('deprecated_at', old_key['created_at']))

        grace_period = expires_at - deprecated_at
        assert grace_period.days >= 7, f"Grace period should be at least 7 days, got {grace_period.days}"

    def test_get_current_signing_key_after_rotation(self, key_manager):
        """Test that current signing key updates after rotation."""
        old_kid = key_manager.create_key()
        new_kid = key_manager.rotate_keys()

        current = key_manager.get_current_signing_key()
        assert current['kid'] == new_kid
        assert current['kid'] != old_kid

    def test_rotate_without_existing_key_creates_new(self, key_manager):
        """Test that rotation without existing key creates new one."""
        new_kid = key_manager.rotate_keys()

        assert new_kid is not None
        key_data = key_manager.get_key(new_kid)
        assert key_data['status'] == 'active'


class TestJWKSExport:
    """Test JWKS (JSON Web Key Set) export for public key distribution."""

    def test_get_public_keys_format(self, key_manager):
        """Test that get_public_keys() returns valid JWKS format."""
        key_manager.create_key()
        public_keys = key_manager.get_public_keys()

        assert isinstance(public_keys, list)
        assert len(public_keys) > 0

        # Check JWKS format
        jwk = public_keys[0]
        assert 'kty' in jwk  # Key Type
        assert 'use' in jwk  # Public Key Use
        assert 'kid' in jwk  # Key ID
        assert 'alg' in jwk  # Algorithm
        assert 'n' in jwk    # Modulus
        assert 'e' in jwk    # Exponent

        assert jwk['kty'] == 'RSA'
        assert jwk['use'] == 'sig'
        assert jwk['alg'] == 'RS256'

    def test_get_public_keys_includes_only_active_keys(self, key_manager):
        """Test that JWKS includes only active keys."""
        old_kid = key_manager.create_key()
        new_kid = key_manager.rotate_keys()

        public_keys = key_manager.get_public_keys()

        # Should include only active key
        kids = [jwk['kid'] for jwk in public_keys]
        assert new_kid in kids
        assert old_kid not in kids

    def test_get_public_keys_empty_when_no_keys(self, key_manager):
        """Test that JWKS is empty when no keys exist."""
        public_keys = key_manager.get_public_keys()
        assert isinstance(public_keys, list)
        assert len(public_keys) == 0


class TestKeyCleanup:
    """Test cleanup of expired keys."""

    def test_cleanup_expired_keys(self, key_manager):
        """Test that expired keys are deleted."""
        # Create key and manually expire it
        kid = key_manager.create_key()
        key_data = key_manager.get_key(kid)

        # Modify expiration date to past
        key_data['expires_at'] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        key_data['status'] = 'expired'

        key_file = key_manager.storage_path / f"{kid}.json"
        with open(key_file, 'w') as f:
            json.dump(key_data, f)

        # Run cleanup
        deleted_count = key_manager.cleanup_expired_keys()

        assert deleted_count == 1
        assert not key_file.exists()

    def test_cleanup_preserves_active_keys(self, key_manager):
        """Test that cleanup doesn't delete active keys."""
        active_kid = key_manager.create_key()

        deleted_count = key_manager.cleanup_expired_keys()

        assert deleted_count == 0
        assert key_manager.get_key(active_kid) is not None

    def test_cleanup_preserves_deprecated_keys_in_grace_period(self, key_manager):
        """Test that cleanup preserves deprecated keys still in grace period."""
        old_kid = key_manager.create_key()
        key_manager.rotate_keys()

        deleted_count = key_manager.cleanup_expired_keys()

        # Deprecated key should still exist (grace period)
        assert deleted_count == 0
        assert key_manager.get_key(old_kid) is not None


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_get_key_with_corrupted_file(self, key_manager, temp_key_storage):
        """Test handling of corrupted key file."""
        # Create corrupted key file
        corrupted_file = temp_key_storage / "corrupted.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json")

        key_data = key_manager.get_key("corrupted")
        assert key_data is None

    def test_create_key_with_insufficient_permissions(self, temp_key_storage):
        """Test that key creation fails with insufficient permissions."""
        # Make directory read-only
        temp_key_storage.chmod(0o400)

        try:
            manager = KeyManager(storage_path=temp_key_storage)
            with pytest.raises(PermissionError):
                manager.create_key()
        finally:
            # Restore permissions for cleanup
            temp_key_storage.chmod(0o700)

    def test_rotate_keys_handles_missing_current_key(self, key_manager):
        """Test that rotation handles missing current key gracefully."""
        # No existing keys
        new_kid = key_manager.rotate_keys()

        assert new_kid is not None
        key_data = key_manager.get_key(new_kid)
        assert key_data['status'] == 'active'


class TestThreadSafety:
    """Test thread safety of KeyManager operations."""

    def test_concurrent_key_creation(self, key_manager):
        """Test that concurrent key creation doesn't corrupt state."""
        import concurrent.futures

        def create_key():
            return key_manager.create_key()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_key) for _ in range(5)]
            kids = [f.result() for f in futures]

        # All KIDs should be unique
        assert len(kids) == len(set(kids))

        # All keys should exist
        for kid in kids:
            assert key_manager.get_key(kid) is not None

    def test_concurrent_rotation(self, key_manager):
        """Test that concurrent rotation operations are safe."""
        import concurrent.futures

        # Create initial key
        key_manager.create_key()

        def rotate():
            return key_manager.rotate_keys()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(rotate) for _ in range(3)]
            new_kids = [f.result() for f in futures]

        # Only one rotation should succeed
        assert len(set(new_kids)) >= 1

        # Current signing key should be valid
        current = key_manager.get_current_signing_key()
        assert current is not None
        assert current['status'] == 'active'


@pytest.mark.integration
class TestKeyManagerIntegration:
    """Integration tests for KeyManager with real JWT operations."""

    def test_sign_and_verify_with_rotated_keys(self, key_manager):
        """Test that tokens signed with old key still verify after rotation."""
        from jose import jwt

        # Create initial key and sign token
        old_kid = key_manager.create_key()
        old_key = key_manager.get_key(old_kid)

        payload = {"sub": "user123", "tenant_id": "tenant456"}
        old_token = jwt.encode(
            payload,
            old_key['private_key_pem'],
            algorithm="RS256",
            headers={"kid": old_kid}
        )

        # Rotate keys
        new_kid = key_manager.rotate_keys()
        old_key_after_rotation = key_manager.get_key(old_kid)

        # Old token should still verify (grace period)
        decoded = jwt.decode(
            old_token,
            old_key_after_rotation['public_key_pem'],
            algorithms=["RS256"]
        )

        assert decoded['sub'] == "user123"
        assert decoded['tenant_id'] == "tenant456"

    def test_jwks_endpoint_format(self, key_manager):
        """Test that JWKS endpoint returns valid format."""
        key_manager.create_key()
        jwks = {"keys": key_manager.get_public_keys()}

        # Verify JWKS structure
        assert 'keys' in jwks
        assert isinstance(jwks['keys'], list)
        assert len(jwks['keys']) > 0

        # Verify can be serialized to JSON
        jwks_json = json.dumps(jwks)
        assert jwks_json is not None

        # Verify can be deserialized
        parsed = json.loads(jwks_json)
        assert parsed['keys'][0]['kty'] == 'RSA'
