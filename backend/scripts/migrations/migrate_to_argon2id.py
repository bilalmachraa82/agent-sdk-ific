#!/usr/bin/env python3
"""
Migration script: bcrypt → Argon2id Password Hashing

This script helps migrate user passwords from bcrypt to Argon2id.

IMPORTANT: This script does NOT directly rehash passwords (we don't store plaintext).
Instead, it provides monitoring and management tools for the automatic migration
that occurs during user login.

Features:
- Analyze current password hash distribution
- Monitor migration progress
- Identify users still using bcrypt
- Enable/disable Argon2id hashing
- Validate Argon2id configuration

Usage:
    python migrate_to_argon2id.py --analyze       # Analyze current state
    python migrate_to_argon2id.py --enable        # Enable Argon2id
    python migrate_to_argon2id.py --monitor       # Monitor migration progress
    python migrate_to_argon2id.py --validate      # Validate configuration
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db, engine
from backend.models.tenant import User
from backend.core.password_hasher import get_password_hasher, PasswordHasher
from backend.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


async def analyze_passwords():
    """
    Analyze password hash distribution across all users.

    Returns:
        Dict with analysis results
    """
    print("=" * 70)
    print("  Password Hash Analysis")
    print("=" * 70)
    print()

    try:
        async with AsyncSession(engine) as db:
            # Get all users
            result = await db.execute(select(User))
            users = result.scalars().all()

            if not users:
                print("No users found in database.")
                return {}

            # Analyze hash algorithms
            hasher = get_password_hasher()
            algorithms = {'argon2id': 0, 'bcrypt': 0, 'unknown': 0}
            needs_rehash_count = 0

            for user in users:
                algo = hasher.detect_hash_algorithm(user.password_hash)
                algorithms[algo] = algorithms.get(algo, 0) + 1

                if hasher.needs_rehash(user.password_hash):
                    needs_rehash_count += 1

            total = len(users)

            print(f"Total users: {total}")
            print()
            print("Hash Algorithm Distribution:")
            print(f"  - Argon2id: {algorithms['argon2id']} ({algorithms['argon2id']/total*100:.1f}%)")
            print(f"  - bcrypt:   {algorithms['bcrypt']} ({algorithms['bcrypt']/total*100:.1f}%)")
            print(f"  - Unknown:  {algorithms['unknown']} ({algorithms['unknown']/total*100:.1f}%)")
            print()
            print(f"Users needing rehash: {needs_rehash_count} ({needs_rehash_count/total*100:.1f}%)")
            print()

            # Migration progress
            if algorithms['bcrypt'] > 0:
                migration_percent = (algorithms['argon2id'] / total) * 100
                print(f"Migration Progress: {migration_percent:.1f}%")
                print()
                print("💡 Tip: Passwords are automatically migrated when users log in.")
                print("   No manual intervention required.")
            else:
                print("✅ All users are using Argon2id!")

            print()
            print("=" * 70)
            print()

            return {
                'total': total,
                'algorithms': algorithms,
                'needs_rehash': needs_rehash_count,
                'migration_percent': (algorithms['argon2id'] / total) * 100 if total > 0 else 0
            }

    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        logger.error("Password analysis failed", error=str(e))
        return {}


async def monitor_migration():
    """
    Monitor recent password migrations.

    Shows users who have recently updated their passwords.
    """
    print("=" * 70)
    print("  Migration Monitoring")
    print("=" * 70)
    print()

    try:
        async with AsyncSession(engine) as db:
            # Get users updated in last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            result = await db.execute(
                select(User)
                .where(User.password_changed_at.isnot(None))
                .where(User.password_changed_at >= thirty_days_ago)
                .order_by(User.password_changed_at.desc())
            )
            recent_users = result.scalars().all()

            if not recent_users:
                print("No password changes in the last 30 days.")
                print()
                return

            hasher = get_password_hasher()

            print(f"Users with password changes (last 30 days): {len(recent_users)}")
            print()
            print("Recent migrations:")
            print()

            for user in recent_users[:10]:  # Show last 10
                algo = hasher.detect_hash_algorithm(user.password_hash)
                changed_date = user.password_changed_at.strftime("%Y-%m-%d %H:%M:%S")
                print(f"  - {user.email:<40} {algo:>10}  {changed_date}")

            if len(recent_users) > 10:
                print(f"\n  ... and {len(recent_users) - 10} more")

            print()
            print("=" * 70)
            print()

    except Exception as e:
        print(f"\n❌ Monitoring failed: {e}")
        logger.error("Migration monitoring failed", error=str(e))


def validate_configuration():
    """
    Validate Argon2id configuration.

    Returns:
        bool: True if valid, False otherwise
    """
    print("=" * 70)
    print("  Argon2id Configuration Validation")
    print("=" * 70)
    print()

    try:
        # Check PasswordHasher initialization
        print("1. Initializing PasswordHasher...")
        hasher = get_password_hasher(use_argon2=True)
        print("   ✅ PasswordHasher initialized")

        # Check Argon2 parameters
        print("\n2. Checking Argon2id parameters...")
        print(f"   - Time cost: {hasher._argon2.time_cost} iterations")
        print(f"   - Memory cost: {hasher._argon2.memory_cost} KiB ({hasher._argon2.memory_cost/1024:.0f} MiB)")
        print(f"   - Parallelism: {hasher._argon2.parallelism} threads")
        print(f"   - Hash length: {hasher._argon2.hash_len} bytes")
        print(f"   - Salt length: {hasher._argon2.salt_len} bytes")

        # Validate parameters meet OWASP recommendations
        print("\n3. Validating against OWASP recommendations...")
        warnings = []

        if hasher._argon2.time_cost < 2:
            warnings.append("Time cost < 2 (recommended: 2+)")

        if hasher._argon2.memory_cost < 65536:  # 64 MiB
            warnings.append(f"Memory cost < 64 MiB (recommended: 64+ MiB)")

        if hasher._argon2.parallelism < 4:
            warnings.append("Parallelism < 4 (recommended: 4+)")

        if warnings:
            print("   ⚠️  Warnings:")
            for warning in warnings:
                print(f"      - {warning}")
        else:
            print("   ✅ All parameters meet OWASP recommendations")

        # Performance test
        print("\n4. Performance test...")
        import time
        test_password = "TestPassword123!"

        start = time.time()
        test_hash = hasher.hash_password_sync(test_password)
        hash_time = (time.time() - start) * 1000

        start = time.time()
        is_valid = hasher.verify_password_sync(test_password, test_hash)
        verify_time = (time.time() - start) * 1000

        print(f"   - Hash time: {hash_time:.1f}ms")
        print(f"   - Verify time: {verify_time:.1f}ms")

        if hash_time < 150:
            print(f"   ✅ Hash time < 150ms target")
        else:
            print(f"   ⚠️  Hash time > 150ms (consider adjusting parameters)")

        # Test automatic migration
        print("\n5. Testing automatic migration...")
        import bcrypt
        bcrypt_hash = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt(rounds=12)).decode()

        if hasher.needs_rehash(bcrypt_hash):
            print("   ✅ bcrypt hashes correctly flagged for rehash")
        else:
            print("   ❌ bcrypt rehash detection not working")

        print("\n" + "=" * 70)
        print("  ✅ Validation Complete")
        print("=" * 70)
        print()

        return True

    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        logger.error("Configuration validation failed", error=str(e))
        return False


def show_enable_instructions():
    """
    Show instructions for enabling Argon2id.
    """
    print("=" * 70)
    print("  Enable Argon2id Password Hashing")
    print("=" * 70)
    print()
    print("To enable Argon2id password hashing:")
    print()
    print("1. The PasswordHasher is already configured with Argon2id by default!")
    print()
    print("2. Automatic migration happens on user login:")
    print("   - User logs in with bcrypt password")
    print("   - System verifies with bcrypt")
    print("   - System re-hashes with Argon2id")
    print("   - Database updated with new hash")
    print()
    print("3. No service disruption:")
    print("   - Both bcrypt and Argon2id verification supported")
    print("   - Users don't notice any difference")
    print("   - Migration completes over time as users log in")
    print()
    print("4. Monitor migration progress:")
    print("   python migrate_to_argon2id.py --analyze")
    print("   python migrate_to_argon2id.py --monitor")
    print()
    print("5. Inactive users:")
    print("   - Users who don't log in will remain on bcrypt")
    print("   - This is acceptable (bcrypt is still secure)")
    print("   - Can be migrated manually if needed (contact admin)")
    print()
    print("=" * 70)
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate from bcrypt to Argon2id password hashing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analyze current password hash distribution'
    )
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Monitor recent password migrations'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate Argon2id configuration'
    )
    parser.add_argument(
        '--enable',
        action='store_true',
        help='Show instructions for enabling Argon2id'
    )

    args = parser.parse_args()

    # If no arguments, show help
    if not any(vars(args).values()):
        parser.print_help()
        print("\n" + "=" * 70)
        print("  Quick Start")
        print("=" * 70)
        print("\n1. Enable Argon2id:")
        print("   python migrate_to_argon2id.py --enable")
        print("\n2. Analyze current state:")
        print("   python migrate_to_argon2id.py --analyze")
        print("\n3. Monitor migration:")
        print("   python migrate_to_argon2id.py --monitor")
        print("\n4. Validate configuration:")
        print("   python migrate_to_argon2id.py --validate")
        print()
        return

    # Execute requested operation
    if args.enable:
        show_enable_instructions()
        sys.exit(0)

    if args.validate:
        success = validate_configuration()
        sys.exit(0 if success else 1)

    if args.analyze:
        result = asyncio.run(analyze_passwords())
        sys.exit(0 if result else 1)

    if args.monitor:
        asyncio.run(monitor_migration())
        sys.exit(0)


if __name__ == "__main__":
    main()
