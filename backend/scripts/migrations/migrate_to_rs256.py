#!/usr/bin/env python3
"""
Migration script: HS256 → RS256 JWT Signing

This script migrates the application from symmetric HS256 JWT signing
to asymmetric RS256 signing with RSA key pairs.

Features:
- Generates initial RSA-4096 key pair
- Updates environment configuration
- Validates KeyManager setup
- Provides rollback instructions
- Zero-downtime migration (both algorithms supported during transition)

Usage:
    python migrate_to_rs256.py --generate      # Generate keys and show instructions
    python migrate_to_rs256.py --validate      # Validate current RS256 setup
    python migrate_to_rs256.py --rollback      # Show rollback instructions
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.key_manager import get_key_manager
from backend.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


def generate_initial_keys():
    """
    Generate initial RSA key pair for RS256 signing.

    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 70)
    print("  RS256 Migration: Generating Initial Key Pair")
    print("=" * 70)
    print()

    try:
        # Initialize KeyManager
        print("1. Initializing KeyManager...")
        key_manager = get_key_manager()

        # Generate initial key pair
        print("2. Generating RSA-4096 key pair (this may take a few seconds)...")
        kid = key_manager.create_key()

        print(f"3. Key generated successfully!")
        print(f"   - Key ID (KID): {kid}")
        print(f"   - Algorithm: RS256")
        print(f"   - Key Size: 4096 bits")
        print(f"   - Storage: {key_manager.storage_path}")

        # Get key info
        key_data = key_manager.get_key(kid)
        print(f"   - Created: {key_data['created_at']}")
        print(f"   - Expires: {key_data['expires_at']}")

        # Verify JWKS endpoint
        print("\n4. Verifying JWKS endpoint...")
        public_keys = key_manager.get_public_keys()
        print(f"   - Public keys available: {len(public_keys)}")

        print("\n" + "=" * 70)
        print("  ✅ Key Generation Complete")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Set environment variable: USE_RS256_JWT=true")
        print("2. Restart your application")
        print("3. Test authentication with new RS256 tokens")
        print("4. Monitor for issues during transition period")
        print("5. After 30 days, deprecate HS256 support")
        print()
        print("JWKS Endpoint: http://localhost:8001/api/v1/auth/.well-known/jwks.json")
        print()
        print("⚠️  IMPORTANT: Keep both USE_RS256_JWT=true and HS256 support")
        print("   enabled for at least 30 days to allow token rotation.")
        print()

        return True

    except Exception as e:
        print(f"\n❌ Error generating keys: {e}")
        logger.error("Key generation failed", error=str(e))
        return False


def validate_setup():
    """
    Validate current RS256 setup.

    Returns:
        bool: True if valid, False otherwise
    """
    print("=" * 70)
    print("  RS256 Setup Validation")
    print("=" * 70)
    print()

    try:
        # Check KeyManager
        print("1. Checking KeyManager initialization...")
        key_manager = get_key_manager()
        print("   ✅ KeyManager initialized")

        # Check for existing keys
        print("\n2. Checking existing keys...")
        current_key = key_manager.get_current_signing_key()

        if not current_key:
            print("   ❌ No signing key found")
            print("\n   Run: python migrate_to_rs256.py --generate")
            return False

        print(f"   ✅ Current signing key: {current_key['kid']}")
        print(f"   - Algorithm: {current_key['algorithm']}")
        print(f"   - Status: {current_key['status']}")
        print(f"   - Expires: {current_key['expires_at']}")

        # Check public keys
        print("\n3. Checking public keys for JWKS...")
        public_keys = key_manager.get_public_keys()
        print(f"   ✅ {len(public_keys)} public key(s) available")

        # Check file permissions
        print("\n4. Checking file permissions...")
        key_dir = key_manager.storage_path
        if key_dir.exists():
            dir_perms = oct(key_dir.stat().st_mode)[-3:]
            if dir_perms == '700':
                print(f"   ✅ Directory permissions: {dir_perms} (secure)")
            else:
                print(f"   ⚠️  Directory permissions: {dir_perms} (should be 700)")

            # Check individual key files
            key_files = list(key_dir.glob("*.json"))
            for key_file in key_files:
                file_perms = oct(key_file.stat().st_mode)[-3:]
                if file_perms != '600':
                    print(f"   ⚠️  File {key_file.name} permissions: {file_perms} (should be 600)")

        # Check environment configuration
        print("\n5. Checking environment configuration...")
        use_rs256 = getattr(settings, 'use_rs256_jwt', False)
        if use_rs256:
            print("   ✅ USE_RS256_JWT=true (RS256 enabled)")
        else:
            print("   ⚠️  USE_RS256_JWT=false (using HS256)")
            print("      Set USE_RS256_JWT=true to enable RS256")

        print("\n" + "=" * 70)
        print("  ✅ Validation Complete")
        print("=" * 70)
        print()

        return True

    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        logger.error("Validation failed", error=str(e))
        return False


def show_rollback_instructions():
    """
    Show instructions for rolling back to HS256.
    """
    print("=" * 70)
    print("  Rollback to HS256")
    print("=" * 70)
    print()
    print("If you need to rollback to HS256 JWT signing:")
    print()
    print("1. Set environment variable: USE_RS256_JWT=false")
    print("   (or remove/comment out the variable)")
    print()
    print("2. Restart your application")
    print()
    print("3. Verify HS256 tokens are being issued:")
    print("   - Login and inspect JWT header")
    print("   - Should see: {\"alg\": \"HS256\"}")
    print()
    print("4. Keep RS256 keys for future migration attempt:")
    print(f"   - Keys stored in: backend/.keys/")
    print("   - Do not delete unless you want to start over")
    print()
    print("⚠️  IMPORTANT: Existing RS256 tokens will still be valid")
    print("   until they expire. Users with RS256 tokens can still")
    print("   authenticate during the transition period.")
    print()
    print("5. If issues persist:")
    print("   - Check logs for specific errors")
    print("   - Verify secret_key is correctly set")
    print("   - Ensure all dependencies are installed")
    print()
    print("=" * 70)
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate from HS256 to RS256 JWT signing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate initial RSA key pair'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate current RS256 setup'
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Show rollback instructions'
    )

    args = parser.parse_args()

    # If no arguments, show help
    if not any(vars(args).values()):
        parser.print_help()
        print("\n" + "=" * 70)
        print("  Quick Start")
        print("=" * 70)
        print("\n1. Generate keys:")
        print("   python migrate_to_rs256.py --generate")
        print("\n2. Validate setup:")
        print("   python migrate_to_rs256.py --validate")
        print("\n3. If needed, rollback:")
        print("   python migrate_to_rs256.py --rollback")
        print()
        return

    # Execute requested operation
    if args.generate:
        success = generate_initial_keys()
        sys.exit(0 if success else 1)

    if args.validate:
        success = validate_setup()
        sys.exit(0 if success else 1)

    if args.rollback:
        show_rollback_instructions()
        sys.exit(0)


if __name__ == "__main__":
    main()
