"""
Re-export AuditLog model from evf.py for cleaner imports
"""

from backend.models.evf import AuditLog

__all__ = ["AuditLog"]