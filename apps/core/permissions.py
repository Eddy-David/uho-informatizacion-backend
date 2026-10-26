"""Permisos RBAC reutilizables por todos los endpoints."""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.core.constants import ACCESS_ROLES, ADMIN_ROLES, CREDENTIAL_ROLES, Role


class HasRole(BasePermission):
    """Permite el acceso solo a los roles indicados en ``allowed_roles``."""

    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        roles = tuple(getattr(view, "allowed_roles", self.allowed_roles))
        return user.role in roles


class IsSuperAdmin(HasRole):
    allowed_roles = (Role.SUPERADMIN,)


class IsAdmin(HasRole):
    allowed_roles = ADMIN_ROLES


class IsSecurityDirector(HasRole):
    allowed_roles = (Role.SUPERADMIN, Role.SECURITY_DIRECTOR)


class IsAccessOperator(HasRole):
    """Personal con acceso a los puntos de control."""

    allowed_roles = ACCESS_ROLES


class IsCredentialManager(HasRole):
    allowed_roles = CREDENTIAL_ROLES


class IsVisitApprover(HasRole):
    allowed_roles = (Role.SUPERADMIN, Role.SECURITY_DIRECTOR, Role.VISIT_APPROVER)


class ReadOnlyOrAdmin(BasePermission):
    """Lectura para usuarios autenticados; escritura solo para administradores."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_superuser or user.role in ADMIN_ROLES


class IsOwnerOrAdmin(BasePermission):
    """Objeto accesible por su dueño (``user``) o por un administrador."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or user.role in ADMIN_ROLES:
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "created_by", None)
        return owner == user
