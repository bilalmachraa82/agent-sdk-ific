"""
Admin endpoints for tenant management and monitoring
Only accessible to users with admin role
"""

from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.core.database import get_db
from backend.api.routers.auth import get_current_active_user
from backend.models.tenant import User, UserRole, Tenant, TenantUsage
from backend.models.evf import EVFProject, AuditLog
from backend.core.logging import setup_logging

router = APIRouter()
logger = setup_logging(__name__)


async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Ensure current user has admin role.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard statistics for the tenant.
    """
    tenant_id = admin_user.tenant_id

    # Get user count
    user_count_result = await db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == tenant_id,
            User.is_active == True
        )
    )
    user_count = user_count_result.scalar() or 0

    # Get EVF project stats
    evf_stats_result = await db.execute(
        select(
            func.count(EVFProject.id).label("total"),
            func.count(EVFProject.id).filter(EVFProject.status == "processing").label("processing"),
            func.count(EVFProject.id).filter(EVFProject.status == "approved").label("approved"),
            func.count(EVFProject.id).filter(EVFProject.status == "rejected").label("rejected")
        ).where(
            EVFProject.tenant_id == tenant_id,
            EVFProject.deleted_at.is_(None)
        )
    )
    evf_stats = evf_stats_result.first()

    # Get current month usage
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage_result = await db.execute(
        select(TenantUsage).where(
            TenantUsage.tenant_id == tenant_id,
            TenantUsage.month == current_month
        )
    )
    usage = usage_result.scalar_one_or_none()

    return {
        "users": {
            "total": user_count
        },
        "evf_projects": {
            "total": evf_stats.total if evf_stats else 0,
            "processing": evf_stats.processing if evf_stats else 0,
            "approved": evf_stats.approved if evf_stats else 0,
            "rejected": evf_stats.rejected if evf_stats else 0
        },
        "current_month_usage": {
            "evfs_processed": usage.evfs_processed if usage else 0,
            "tokens_consumed": usage.tokens_consumed if usage else 0,
            "cost_euros": float(usage.cost_euros) if usage else 0
        }
    }


@router.get("/users")
async def list_tenant_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users in the tenant.
    """
    result = await db.execute(
        select(User).where(
            User.tenant_id == admin_user.tenant_id
        ).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return users


@router.post("/users")
async def create_user(
    email: str,
    full_name: str,
    role: UserRole = UserRole.VIEWER,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user in the tenant.
    """
    # Check if email already exists in tenant
    existing_user = await db.execute(
        select(User).where(
            User.email == email,
            User.tenant_id == admin_user.tenant_id
        )
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Create new user
    from backend.core.security import async_get_password_hash
    import secrets

    # Generate random password
    temp_password = secrets.token_urlsafe(16)

    user = User(
        email=email,
        full_name=full_name,
        password_hash=await async_get_password_hash(temp_password),
        role=role,
        tenant_id=admin_user.tenant_id,
        is_active=True
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        "User created by admin",
        new_user_id=str(user.id),
        admin_id=str(admin_user.id),
        tenant_id=str(admin_user.tenant_id)
    )

    # TODO: Send email with temp password

    return {
        "user": user,
        "temp_password": temp_password  # In production, send via email
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user's role or status.
    """
    # Get user
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == admin_user.tenant_id
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deactivation
    if user_id == admin_user.id and is_active == False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    # Update fields
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active

    await db.commit()

    logger.info(
        "User updated by admin",
        user_id=str(user_id),
        admin_id=str(admin_user.id),
        changes={"role": role, "is_active": is_active}
    )

    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user from the tenant.
    """
    # Prevent self-deletion
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Get user
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == admin_user.tenant_id
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Soft delete
    user.is_active = False
    user.deleted_at = datetime.utcnow()
    await db.commit()

    logger.info(
        "User deleted by admin",
        user_id=str(user_id),
        admin_id=str(admin_user.id)
    )

    return {"message": "User deleted successfully"}


@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    user_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs for the tenant with filtering.
    """
    query = select(AuditLog).where(
        AuditLog.tenant_id == admin_user.tenant_id
    )

    # Apply filters
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    query = query.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())

    result = await db.execute(query)
    logs = result.scalars().all()

    return logs


@router.get("/tenant/info")
async def get_tenant_info(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant information and settings.
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == admin_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    return tenant


@router.put("/tenant/settings")
async def update_tenant_settings(
    settings: dict,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant settings.
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == admin_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Merge settings
    tenant.settings = {**tenant.settings, **settings}
    await db.commit()

    logger.info(
        "Tenant settings updated",
        tenant_id=str(admin_user.tenant_id),
        admin_id=str(admin_user.id)
    )

    return tenant