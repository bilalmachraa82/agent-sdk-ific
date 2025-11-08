"""
Seed data script for EVF Portugal 2030 backend.
Creates demo tenant, users, company, and sample EVF project.

Usage:
    python backend/seed_data.py

This script is idempotent - safe to run multiple times.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database import db_manager
from backend.core.security import security
from backend.models import (
    Tenant, User, Company, TenantCompanyAccess,
    EVFProject, TenantUsage,
    TenantPlan, UserRole, EVFStatus, FundType
)


# Demo data configuration
DEMO_TENANT = {
    "slug": "demo",
    "name": "Demo Consultoria Lda",
    "nif": "123456789",
    "plan": TenantPlan.PROFESSIONAL,
    "mrr": 299.00,
    "email": "contato@demo.pt",
    "phone": "+351 211 234 567",
    "website": "https://demo.pt",
    "address": "Av. da Liberdade 123, 3º Andar",
    "city": "Lisboa",
    "postal_code": "1250-140",
    "is_active": True,
    "is_verified": True,
    "settings": {
        "max_evfs_per_month": 50,
        "enable_auto_compliance_check": True,
        "enable_ai_narrative": True,
        "timezone": "Europe/Lisbon",
        "language": "pt-PT",
    },
}

DEMO_ADMIN = {
    "email": "admin@demo.pt",
    "password": "Demo@2024",  # Will be hashed
    "full_name": "Admin Demo",
    "role": UserRole.ADMIN,
    "phone": "+351 911 234 567",
    "department": "Gestão",
    "is_active": True,
    "is_verified": True,
}

DEMO_COMPANY = {
    "nif": "987654321",
    "name": "Empresa Exemplo Lda",
    "cae_code": "62010",  # Software development
    "email": "info@empresaexemplo.pt",
    "phone": "+351 211 987 654",
    "website": "https://empresaexemplo.pt",
    "address": "Rua das Flores 456",
    "custom_metadata": {
        "sector": "Technology",
        "employees": 25,
        "founded_year": 2018,
    },
}

DEMO_PROJECT = {
    "name": "Projeto Indústria 4.0",
    "description": "Implementação de sistema MES para automação da produção com integração IoT e análise de dados em tempo real.",
    "fund_type": FundType.PT2030,
    "status": EVFStatus.DRAFT,
    "project_start_year": 2025,
    "project_end_year": 2027,
    "project_duration_years": 3,
    "total_investment": 500000.00,
    "eligible_investment": 450000.00,
    "funding_requested": 225000.00,
    "notes": "Projeto piloto para demonstração da plataforma EVF Portugal 2030",
    "custom_metadata": {
        "demo": True,
        "created_via": "seed_script",
    },
}


async def create_demo_tenant(session):
    """Create or retrieve demo tenant."""
    print("\n📦 Creating demo tenant...")

    # Check if tenant already exists
    result = await session.execute(
        select(Tenant).where(Tenant.slug == DEMO_TENANT["slug"])
    )
    existing_tenant = result.scalar_one_or_none()

    if existing_tenant:
        print(f"   ✓ Tenant '{existing_tenant.name}' already exists (ID: {existing_tenant.id})")
        return existing_tenant

    # Create new tenant
    tenant = Tenant(**DEMO_TENANT)
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    print(f"   ✓ Created tenant '{tenant.name}' (ID: {tenant.id})")
    return tenant


async def create_demo_admin(session, tenant_id):
    """Create or retrieve demo admin user."""
    print("\n👤 Creating demo admin user...")

    # Check if user already exists
    result = await session.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.email == DEMO_ADMIN["email"]
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        print(f"   ✓ User '{existing_user.email}' already exists (ID: {existing_user.id})")
        return existing_user

    # Create new user
    user_data = DEMO_ADMIN.copy()
    password = user_data.pop("password")
    user_data["password_hash"] = security.hash_password(password)
    user_data["tenant_id"] = tenant_id

    user = User(**user_data)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    print(f"   ✓ Created user '{user.email}' (ID: {user.id})")
    print(f"   ℹ  Login credentials: {DEMO_ADMIN['email']} / {password}")
    return user


async def create_demo_company(session):
    """Create or retrieve demo company."""
    print("\n🏢 Creating demo company...")

    # Check if company already exists
    result = await session.execute(
        select(Company).where(Company.nif == DEMO_COMPANY["nif"])
    )
    existing_company = result.scalar_one_or_none()

    if existing_company:
        print(f"   ✓ Company '{existing_company.name}' already exists (ID: {existing_company.id})")
        return existing_company

    # Create new company
    company = Company(**DEMO_COMPANY)
    session.add(company)
    await session.commit()
    await session.refresh(company)

    print(f"   ✓ Created company '{company.name}' (ID: {company.id})")
    return company


async def link_tenant_to_company(session, tenant_id, company_id, admin_user_id):
    """Create tenant-company access relationship."""
    print("\n🔗 Linking tenant to company...")

    # Check if relationship already exists
    result = await session.execute(
        select(TenantCompanyAccess).where(
            TenantCompanyAccess.tenant_id == tenant_id,
            TenantCompanyAccess.company_id == company_id
        )
    )
    existing_access = result.scalar_one_or_none()

    if existing_access:
        print(f"   ✓ Tenant-company access already exists")
        return existing_access

    # Create new relationship
    access = TenantCompanyAccess(
        tenant_id=tenant_id,
        company_id=company_id,
        added_by=admin_user_id,
        notes="Created via seed script"
    )
    session.add(access)
    await session.commit()
    await session.refresh(access)

    print(f"   ✓ Linked tenant to company")
    return access


async def create_demo_project(session, tenant_id, company_id, admin_user_id):
    """Create demo EVF project."""
    print("\n📋 Creating demo EVF project...")

    # Check if project already exists
    result = await session.execute(
        select(EVFProject).where(
            EVFProject.tenant_id == tenant_id,
            EVFProject.name == DEMO_PROJECT["name"]
        )
    )
    existing_project = result.scalar_one_or_none()

    if existing_project:
        print(f"   ✓ Project '{existing_project.name}' already exists (ID: {existing_project.id})")
        return existing_project

    # Create new project
    project_data = DEMO_PROJECT.copy()
    project_data["tenant_id"] = tenant_id
    project_data["company_id"] = company_id
    project_data["created_by"] = admin_user_id

    project = EVFProject(**project_data)
    session.add(project)
    await session.commit()
    await session.refresh(project)

    print(f"   ✓ Created project '{project.name}' (ID: {project.id})")
    return project


async def create_tenant_usage(session, tenant_id):
    """Create current month usage tracking."""
    print("\n📊 Creating usage tracking...")

    # Get first day of current month
    now = datetime.utcnow()
    current_month = datetime(now.year, now.month, 1)

    # Check if usage already exists
    result = await session.execute(
        select(TenantUsage).where(
            TenantUsage.tenant_id == tenant_id,
            TenantUsage.month == current_month
        )
    )
    existing_usage = result.scalar_one_or_none()

    if existing_usage:
        print(f"   ✓ Usage tracking already exists for {current_month.strftime('%Y-%m')}")
        return existing_usage

    # Create new usage record
    usage = TenantUsage(
        tenant_id=tenant_id,
        month=current_month,
        evfs_processed=0,
        tokens_consumed=0,
        storage_mb=0,
        cost_euros=0,
        storage_cost_euros=0,
        ai_cost_euros=0,
    )
    session.add(usage)
    await session.commit()
    await session.refresh(usage)

    print(f"   ✓ Created usage tracking for {current_month.strftime('%Y-%m')}")
    return usage


async def seed_database():
    """Main seeding function."""
    print("=" * 60)
    print("EVF Portugal 2030 - Database Seed Script")
    print("=" * 60)

    try:
        # Initialize database connection
        await db_manager.initialize()

        async with db_manager.get_db_context() as session:
            # Create entities in order
            tenant = await create_demo_tenant(session)
            admin = await create_demo_admin(session, tenant.id)
            company = await create_demo_company(session)
            access = await link_tenant_to_company(session, tenant.id, company.id, admin.id)
            project = await create_demo_project(session, tenant.id, company.id, admin.id)
            usage = await create_tenant_usage(session, tenant.id)

            print("\n" + "=" * 60)
            print("✅ Database seeding completed successfully!")
            print("=" * 60)
            print("\n📌 Summary:")
            print(f"   Tenant ID:  {tenant.id}")
            print(f"   Tenant Slug: {tenant.slug}")
            print(f"   Admin Email: {admin.email}")
            print(f"   Admin Password: Demo@2024")
            print(f"   Company ID: {company.id}")
            print(f"   Project ID: {project.id}")
            print(f"\n🚀 You can now start the API and login with:")
            print(f"   Email: admin@demo.pt")
            print(f"   Password: Demo@2024")
            print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await db_manager.close()


def main():
    """Entry point for the script."""
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
