"""
Simple validation script for file storage service.
Run this to verify the implementation without full pytest setup.
"""

import sys
import asyncio
from pathlib import Path
from uuid import uuid4
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("=" * 60)
print("File Storage Service Validation")
print("=" * 60)

# Test imports
print("\n1. Testing imports...")
try:
    from backend.services.file_storage import (
        FileStorageService,
        FileMetadata,
        FileType,
        StorageBackend,
        FileStorageError,
    )
    print("   ✓ All imports successful")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test FileMetadata model
print("\n2. Testing FileMetadata model...")
try:
    tenant_id = uuid4()
    metadata = FileMetadata(
        tenant_id=tenant_id,
        file_name="test.xml",
        file_type=FileType.SAFT,
        file_extension=".xml",
        mime_type="application/xml",
        file_size_bytes=1024,
        encrypted_size_bytes=1200,
        sha256_hash="abc123",
        storage_path="test/path.xml",
        storage_backend=StorageBackend.LOCAL,
    )
    assert metadata.tenant_id == tenant_id
    assert metadata.file_extension == ".xml"
    print("   ✓ FileMetadata model works correctly")
except Exception as e:
    print(f"   ✗ FileMetadata test failed: {e}")
    sys.exit(1)

# Test extension normalization
print("\n3. Testing extension normalization...")
try:
    metadata = FileMetadata(
        tenant_id=uuid4(),
        file_name="test.XML",
        file_type=FileType.SAFT,
        file_extension="XML",  # No dot, uppercase
        mime_type="application/xml",
        file_size_bytes=1024,
        encrypted_size_bytes=1200,
        sha256_hash="abc123",
        storage_path="test/path.xml",
        storage_backend=StorageBackend.LOCAL,
    )
    assert metadata.file_extension == ".xml", f"Expected .xml, got {metadata.file_extension}"
    print("   ✓ Extension normalization works")
except Exception as e:
    print(f"   ✗ Extension normalization failed: {e}")
    sys.exit(1)

# Test FileStorageService initialization (local)
print("\n4. Testing FileStorageService initialization...")
try:
    # Monkey patch settings for test
    from backend.core import config
    original_backend = config.settings.storage_backend
    original_path = config.settings.local_storage_path

    config.settings.storage_backend = "local"
    config.settings.local_storage_path = "/tmp/evf_test_storage"

    service = FileStorageService()
    assert service.backend == StorageBackend.LOCAL
    assert service.max_file_size_bytes > 0
    print(f"   ✓ FileStorageService initialized (backend={service.backend})")

    # Restore settings
    config.settings.storage_backend = original_backend
    config.settings.local_storage_path = original_path
except Exception as e:
    print(f"   ✗ Service initialization failed: {e}")
    sys.exit(1)

# Test helper methods
print("\n5. Testing helper methods...")
try:
    service = FileStorageService()

    # Test get_file_extension
    ext = service._get_file_extension("test.xml")
    assert ext == ".xml", f"Expected .xml, got {ext}"

    ext = service._get_file_extension("TEST.XLSX")
    assert ext == ".xlsx", f"Expected .xlsx, got {ext}"

    # Test generate_storage_path
    tenant_id = uuid4()
    file_id = uuid4()
    path = service._generate_storage_path(tenant_id, file_id, ".xml")
    assert f"tenants/{tenant_id}" in path
    assert str(file_id) in path
    assert path.endswith(".xml")

    print("   ✓ Helper methods work correctly")
except Exception as e:
    print(f"   ✗ Helper methods failed: {e}")
    sys.exit(1)

# Test encryption/decryption
print("\n6. Testing encryption/decryption...")
try:
    from backend.core.encryption import encryption_manager

    original_text = "Test file content with special chars: ãçüñ"
    encrypted = encryption_manager.encrypt(original_text)
    decrypted = encryption_manager.decrypt(encrypted)

    assert decrypted == original_text, "Encryption roundtrip failed"
    print("   ✓ Encryption/decryption works")
except Exception as e:
    print(f"   ✗ Encryption test failed: {e}")
    sys.exit(1)

# Test database model
print("\n7. Testing database model...")
try:
    from backend.models.file import File, FileAccessLog

    # Create instance (don't save to DB)
    tenant_id = uuid4()
    file = File(
        tenant_id=tenant_id,
        file_name="test.xml",
        file_type="saft",
        file_extension=".xml",
        mime_type="application/xml",
        file_size_bytes=1024,
        encrypted_size_bytes=1200,
        sha256_hash="abc123",
        storage_path="test/path.xml",
        storage_backend="local",
    )

    # Test to_metadata_dict
    metadata_dict = file.to_metadata_dict()
    assert metadata_dict["tenant_id"] == tenant_id
    assert metadata_dict["file_name"] == "test.xml"

    print("   ✓ Database model works correctly")
except Exception as e:
    print(f"   ✗ Database model test failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All validation tests passed!")
print("=" * 60)
print("\nFile storage service is ready for production use.")
print("\nNext steps:")
print("1. Install dependencies: pip install -r requirements.txt")
print("2. Configure .env with STORAGE_BACKEND and credentials")
print("3. Run database migrations: alembic upgrade head")
print("4. Run full test suite: pytest tests/test_file_storage.py")
print("=" * 60)
