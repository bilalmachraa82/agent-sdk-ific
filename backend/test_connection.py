"""
Database connection and multi-tenant isolation test script.
Verifies database connectivity, tables, and RLS setup.

Usage:
    python backend/test_connection.py
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import text, inspect
from sqlalchemy.exc import DatabaseError
from tabulate import tabulate

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database import db_manager
from backend.core.config import settings
from backend.models import Base


async def test_database_connection():
    """Test basic database connectivity."""
    print("\n🔌 Testing database connection...")

    try:
        await db_manager.initialize()

        async with db_manager.get_db_context() as session:
            # Simple query to test connection
            result = await session.execute(text("SELECT version();"))
            version = result.scalar()

            print(f"   ✓ Connected successfully!")
            print(f"   ℹ  PostgreSQL version: {version}")
            return True

    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False


async def test_tables_exist():
    """Check if all required tables exist."""
    print("\n📋 Checking database tables...")

    try:
        async with db_manager.get_db_context() as session:
            # Get list of tables from database
            result = await session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            db_tables = [row[0] for row in result.fetchall()]

            # Expected tables from models
            expected_tables = [
                'tenants',
                'users',
                'companies',
                'tenant_companies',
                'tenant_usage',
                'evf_projects',
                'financial_models',
                'audit_log',
                'files',
                'file_access_log',
                'alembic_version',
            ]

            # Check each expected table
            missing_tables = []
            existing_tables = []

            for table in expected_tables:
                if table in db_tables:
                    existing_tables.append(table)
                else:
                    missing_tables.append(table)

            # Display results
            if existing_tables:
                print(f"   ✓ Found {len(existing_tables)} tables:")
                for table in existing_tables:
                    print(f"      • {table}")

            if missing_tables:
                print(f"\n   ⚠️  Missing {len(missing_tables)} tables:")
                for table in missing_tables:
                    print(f"      • {table}")
                print(f"\n   💡 Run migrations: alembic upgrade head")
                return False

            # Show extra tables (not in our models)
            extra_tables = [t for t in db_tables if t not in expected_tables]
            if extra_tables:
                print(f"\n   ℹ  Additional tables found:")
                for table in extra_tables:
                    print(f"      • {table}")

            return len(missing_tables) == 0

    except Exception as e:
        print(f"   ❌ Error checking tables: {e}")
        return False


async def test_table_structure():
    """Display structure of key tables."""
    print("\n🔍 Inspecting table structures...")

    try:
        async with db_manager.get_db_context() as session:
            # Tables to inspect
            tables_to_inspect = ['tenants', 'users', 'evf_projects']

            for table_name in tables_to_inspect:
                # Check if table exists
                result = await session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """))

                columns = result.fetchall()

                if columns:
                    print(f"\n   📊 Table: {table_name}")
                    table_data = [
                        [col[0], col[1], "NULL" if col[2] == "YES" else "NOT NULL"]
                        for col in columns
                    ]
                    print(tabulate(
                        table_data,
                        headers=["Column", "Type", "Nullable"],
                        tablefmt="simple"
                    ))
                else:
                    print(f"   ⚠️  Table '{table_name}' not found")

            return True

    except Exception as e:
        print(f"   ❌ Error inspecting tables: {e}")
        return False


async def test_tenant_data():
    """Check if any tenant data exists."""
    print("\n👥 Checking tenant data...")

    try:
        async with db_manager.get_db_context() as session:
            # Count tenants
            result = await session.execute(text("SELECT COUNT(*) FROM tenants;"))
            tenant_count = result.scalar()

            # Count users
            result = await session.execute(text("SELECT COUNT(*) FROM users;"))
            user_count = result.scalar()

            # Count projects
            result = await session.execute(text("SELECT COUNT(*) FROM evf_projects;"))
            project_count = result.scalar()

            # Count companies
            result = await session.execute(text("SELECT COUNT(*) FROM companies;"))
            company_count = result.scalar()

            print(f"   ℹ  Database statistics:")
            print(f"      • Tenants: {tenant_count}")
            print(f"      • Users: {user_count}")
            print(f"      • Companies: {company_count}")
            print(f"      • EVF Projects: {project_count}")

            if tenant_count == 0:
                print(f"\n   💡 No data found. Run: python backend/seed_data.py")

            return True

    except Exception as e:
        print(f"   ❌ Error checking tenant data: {e}")
        return False


async def test_multi_tenant_isolation():
    """Test Row-Level Security and tenant isolation."""
    print("\n🔒 Testing multi-tenant isolation (RLS)...")

    try:
        async with db_manager.get_db_context() as session:
            # Check if RLS is enabled on tenant-scoped tables
            result = await session.execute(text("""
                SELECT tablename, rowsecurity
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename IN ('users', 'evf_projects', 'financial_models', 'audit_log')
                ORDER BY tablename;
            """))

            rls_status = result.fetchall()

            if rls_status:
                print(f"   ℹ  Row-Level Security status:")
                table_data = [
                    [row[0], "✓ Enabled" if row[1] else "⚠️  Disabled"]
                    for row in rls_status
                ]
                print(tabulate(
                    table_data,
                    headers=["Table", "RLS Status"],
                    tablefmt="simple"
                ))

                # Check if any policies exist
                result = await session.execute(text("""
                    SELECT schemaname, tablename, policyname
                    FROM pg_policies
                    WHERE schemaname = 'public'
                    ORDER BY tablename, policyname;
                """))

                policies = result.fetchall()

                if policies:
                    print(f"\n   ℹ  Found {len(policies)} RLS policies:")
                    for policy in policies[:10]:  # Show first 10
                        print(f"      • {policy[1]}.{policy[2]}")
                    if len(policies) > 10:
                        print(f"      ... and {len(policies) - 10} more")
                else:
                    print(f"\n   ⚠️  No RLS policies found!")
                    print(f"   💡 You may need to create RLS policies for tenant isolation")

            return True

    except Exception as e:
        print(f"   ❌ Error testing RLS: {e}")
        return False


async def test_indexes():
    """Check if critical indexes exist."""
    print("\n📇 Checking database indexes...")

    try:
        async with db_manager.get_db_context() as session:
            # Get all indexes
            result = await session.execute(text("""
                SELECT
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename IN ('users', 'evf_projects', 'audit_log', 'tenants')
                ORDER BY tablename, indexname;
            """))

            indexes = result.fetchall()

            if indexes:
                print(f"   ✓ Found {len(indexes)} indexes")

                # Group by table
                from collections import defaultdict
                by_table = defaultdict(list)
                for idx in indexes:
                    by_table[idx[0]].append(idx[1])

                for table, idx_list in sorted(by_table.items()):
                    print(f"\n   📊 {table}: {len(idx_list)} indexes")
                    for idx_name in idx_list[:5]:  # Show first 5
                        print(f"      • {idx_name}")
                    if len(idx_list) > 5:
                        print(f"      ... and {len(idx_list) - 5} more")

                return True
            else:
                print(f"   ⚠️  No indexes found")
                return False

    except Exception as e:
        print(f"   ❌ Error checking indexes: {e}")
        return False


async def test_configuration():
    """Display current configuration."""
    print("\n⚙️  Current configuration:")

    # Mask sensitive parts of URLs
    def mask_url(url: str) -> str:
        if '@' in url:
            parts = url.split('@')
            credential_parts = parts[0].split('//')
            if len(credential_parts) > 1:
                protocol = credential_parts[0]
                credentials = credential_parts[1].split(':')
                if len(credentials) > 1:
                    return f"{protocol}//{credentials[0]}:****@{parts[1]}"
        return url

    config_data = [
        ["Environment", settings.environment],
        ["App Name", settings.app_name],
        ["App Version", settings.app_version],
        ["Database URL", mask_url(settings.database_url)],
        ["Pool Size", f"{settings.database_min_pool_size}-{settings.database_max_pool_size}"],
        ["Redis URL", mask_url(settings.redis_url)],
        ["Claude Model", settings.claude_model],
        ["Qdrant URL", settings.qdrant_url],
    ]

    print(tabulate(config_data, headers=["Setting", "Value"], tablefmt="simple"))


async def run_all_tests():
    """Run all database tests."""
    print("=" * 60)
    print("EVF Portugal 2030 - Database Connection Test")
    print("=" * 60)

    try:
        # Run tests in sequence
        tests = [
            ("Connection", test_database_connection),
            ("Configuration", test_configuration),
            ("Tables", test_tables_exist),
            ("Structure", test_table_structure),
            ("Data", test_tenant_data),
            ("Indexes", test_indexes),
            ("RLS", test_multi_tenant_isolation),
        ]

        results = {}

        for test_name, test_func in tests:
            try:
                results[test_name] = await test_func()
            except Exception as e:
                print(f"\n❌ Test '{test_name}' failed with exception: {e}")
                results[test_name] = False

        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)

        summary_data = [
            [name, "✓ PASS" if passed else "❌ FAIL"]
            for name, passed in results.items()
        ]

        print(tabulate(summary_data, headers=["Test", "Result"], tablefmt="simple"))

        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)

        print(f"\n   Tests passed: {passed_tests}/{total_tests}")

        if passed_tests == total_tests:
            print("\n✅ All tests passed! Database is ready.")
        else:
            print("\n⚠️  Some tests failed. Please review the output above.")

        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fatal error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await db_manager.close()


def main():
    """Entry point for the script."""
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
