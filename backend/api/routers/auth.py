"""
Authentication and authorization endpoints
JWT-based auth with multi-tenant support
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    async_verify_password,
    async_get_password_hash,
    decode_token
)
from backend.core.config import settings
from backend.core.logging import setup_logging, create_audit_log
from backend.models.tenant import User, Tenant
from backend.schemas.auth import (
    UserCreate,
    UserLogin,
    Token,
    TokenRefresh,
    UserResponse,
    TenantCreate,
    RegistrationRequest
)

router = APIRouter()
logger = setup_logging(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")

        if user_id is None or tenant_id is None:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    # Get user from database
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


@router.post("/register", response_model=Token)
async def register(
    data: RegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new tenant and initial admin user.
    This creates both the tenant and the first admin user.
    Returns access and refresh tokens for immediate login.
    """

    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if tenant slug already exists
    result = await db.execute(
        select(Tenant).where(Tenant.slug == data.tenant_slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant slug already exists"
        )

    # Check if NIF already exists
    result = await db.execute(
        select(Tenant).where(Tenant.nif == data.tenant_nif)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NIF already registered"
        )

    try:
        # Create tenant
        tenant = Tenant(
            name=data.tenant_name,
            slug=data.tenant_slug,
            nif=data.tenant_nif,
            plan="starter",
            is_active=True,
            settings={}
        )
        db.add(tenant)
        await db.flush()  # Get tenant ID

        # Create admin user
        user = User(
            email=data.email,
            full_name=data.full_name,
            password_hash=await async_get_password_hash(data.password),
            tenant_id=tenant.id,
            role="admin",
            is_active=True,
            is_verified=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Log registration
        logger.info(
            "New tenant registered",
            tenant_id=str(tenant.id),
            tenant_name=tenant.name,
            user_email=user.email
        )

        # Create audit log
        audit = create_audit_log(
            action="REGISTER",
            entity_type="tenant",
            entity_id=str(tenant.id),
            tenant_id=str(tenant.id),
            user_id=str(user.id),
            metadata={"tenant_name": tenant.name, "user_email": user.email}
        )
        logger.info("Audit log", **audit)

        # Create tokens for immediate login
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role
            },
            tenant_id=str(user.tenant_id)
        )
        refresh_token = create_refresh_token(
            data={
                "sub": str(user.id)
            },
            tenant_id=str(user.tenant_id)
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_expiration_minutes * 60
        }

    except Exception as e:
        await db.rollback()
        logger.error("Registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    Returns access and refresh tokens.
    """

    # Find user by email
    result = await db.execute(
        select(User).where(
            User.email == form_data.username,  # OAuth2 uses 'username' field
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    # Verify user and password
    if not user or not await async_verify_password(form_data.password, user.password_hash):
        logger.warning(
            "Failed login attempt",
            email=form_data.username
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        },
        tenant_id=str(user.tenant_id)
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id)
        },
        tenant_id=str(user.tenant_id)
    )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    logger.info(
        "User logged in",
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expiration_minutes * 60
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    try:
        payload = decode_token(refresh_data.refresh_token)
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Get user
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.is_active == True
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Create new access token
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role
            },
            tenant_id=str(user.tenant_id)
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_data.refresh_token,  # Return same refresh token
            "token_type": "bearer",
            "expires_in": settings.jwt_expiration_minutes * 60
        }

    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    """
    return current_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout current user.
    In a stateless JWT system, this mainly logs the event.
    The client should discard the token.
    """

    logger.info(
        "User logged out",
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id)
    )

    # Could implement token blacklisting here if needed

    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    current_password: str = Body(...),
    new_password: str = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change current user's password.
    """

    # Verify current password
    if not await async_verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Update password
    current_user.password_hash = await async_get_password_hash(new_password)
    current_user.password_changed_at = datetime.utcnow()
    await db.commit()

    logger.info(
        "Password changed",
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id)
    )

    return {"message": "Password successfully changed"}