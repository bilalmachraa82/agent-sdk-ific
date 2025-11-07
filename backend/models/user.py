"""
Re-export User model from tenant.py for cleaner imports
"""

from backend.models.tenant import User, UserRole

__all__ = ["User", "UserRole"]