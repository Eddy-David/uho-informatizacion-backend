"""
Resolución de permisos efectivos (RBAC) y permisos DRF.

Flujo:

    usuario.role ──► Role.permissions (BD, editable por SA)
                            │
                            └── si el rol no existe en BD: permisos por defecto
                                de ``ROLE_DEFINITIONS`` (constants._DEFAULT_BY_ROLE)

El resultado se cachea por rol para no consultar la BD en cada petición.
"""

from __future__ import annotations

from django.core.cache import cache

from apps.usuarios.constants import (
    ALL_PERMISSIONS,
    FULL_ACCESS_ROLES,
    Permission,
    RoleCode,
    default_permissions_for,
    role_definition,
)

CACHE_KEY = "sigacu:rbac:role:{code}"
CACHE_TTL = 300  # segundos


def role_permissions(role_code: str) -> frozenset[str]:
    """Permisos otorgados a un rol (incluye ``*`` para acceso total)."""
    if not role_code:
        return frozenset()

    cache_key = CACHE_KEY.format(code=role_code)
    cached = cache.get(cache_key)
    if cached is not None:
        return frozenset(cached)

    from apps.usuarios.models import RoleDefinition

    role = RoleDefinition.objects.filter(code=role_code, is_active=True).first()
    if role is not None:
        permissions = frozenset(p for p in role.permissions if p in ALL_PERMISSIONS or p == "*")
    else:
        # Rol sin registro en BD: usar los valores por defecto del código.
        permissions = frozenset(
            p for p in default_permissions_for(role_code) if p in ALL_PERMISSIONS or p == "*"
        )

    cache.set(cache_key, sorted(permissions), CACHE_TTL)
    return permissions


def invalidate_role_cache(role_code: str | None = None) -> None:
    """Invalida la caché de uno o de todos los roles."""
    from apps.usuarios.constants import ROLE_DEFINITIONS

    codes = [role_code] if role_code else list(ROLE_DEFINITIONS)
    for code in codes:
        cache.delete(CACHE_KEY.format(code=code))


def effective_permissions(user) -> list[str]:
    """Permisos efectivos del usuario, ordenados y sin duplicados."""
    if not user or not getattr(user, "is_authenticated", False):
        return []
    if getattr(user, "is_superuser", False) or user.role in FULL_ACCESS_ROLES:
        return ["*"]

    granted = set(role_permissions(user.role))
    if "*" in granted:
        return ["*"]

    # Permisos granular adicionales (concesiones puntuales por usuario).
    granted |= {p for p in getattr(user, "extra_permissions", []) or [] if p in ALL_PERMISSIONS}
    return sorted(granted)


def user_has(user, *required: str, require_all: bool = True) -> bool:
    """Comprueba si el usuario posee los permisos indicados.

    ``require_all=True``  → debe tener todos.
    ``require_all=False`` → basta con uno.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or user.role in FULL_ACCESS_ROLES:
        return True

    granted = role_permissions(user.role)
    if "*" in granted:
        return True
    granted = granted | {
        p for p in getattr(user, "extra_permissions", []) or [] if p in ALL_PERMISSIONS
    }

    check = all if require_all else any
    return check(perm in granted for perm in required)


def permissions_by_module() -> list[dict]:
    """Agrupa los permisos por recurso (``<recurso>:<accion>``) para la UI."""
    grouped: dict[str, list[dict]] = {}
    for perm in Permission:
        resource, _, action = perm.value.partition(":")
        grouped.setdefault(resource, []).append(
            {"code": perm.value, "action": action, "label": str(perm.label)}
        )
    return [
        {"resource": resource, "permissions": items} for resource, items in sorted(grouped.items())
    ]


def role_matrix() -> list[dict]:
    """Matriz completa de roles (BD + por defecto) para la pantalla de administración."""
    from apps.usuarios.models import RoleDefinition

    stored = {role.code: role for role in RoleDefinition.objects.all()}
    matrix = []
    for code in RoleCode:
        meta = role_definition(code.value)
        role = stored.get(code.value)
        matrix.append(
            {
                **meta,
                "permissions": sorted(role.permissions) if role else meta["permissions"],
                "is_active": role.is_active if role else True,
                "user_count": role.users.filter(estado=True).count() if role else 0,
            }
        )
    return matrix


# ---------------------------------------------------------------------------
# Permisos DRF
# ---------------------------------------------------------------------------
from rest_framework.permissions import SAFE_METHODS, BasePermission  # noqa: E402


class HasPerm(BasePermission):
    """Verifica ``required_permissions`` declarados en la vista.

    Uso::

        class AccessLogViewSet(viewsets.ReadOnlyModelViewSet):
            permission_classes = [IsAuthenticated, HasPerm(Permission.ACCESS_VIEW)]
    """

    def __init__(self, *permissions: str, require_all: bool = True):
        self.required_permissions = permissions
        self.require_all = require_all
        super().__init__()

    def has_permission(self, request, view):
        required = getattr(view, "required_permissions", None) or self.required_permissions
        if not required:
            return True
        return user_has(request.user, *required, require_all=self.require_all)

    def __call__(self):
        # Permite usar ``HasPerm(...)`` directamente en ``permission_classes``.
        return self


class HasPermForWrite(HasPerm):
    """Lectura libre (autenticado) y escritura solo con el permiso indicado."""

    def __init__(self, write_permission: str, read_permission: str | None = None):
        super().__init__(write_permission)
        self.read_permission = read_permission or write_permission

    def has_permission(self, request, view):
        permission = (
            self.read_permission if request.method in SAFE_METHODS else self.required_permissions[0]
        )
        return user_has(request.user, permission)


class ReadOnly(HasPerm):
    def __init__(self):
        super().__init__()


class IsSuperAdmin(BasePermission):
    """Solo el rol ``SA`` (o un superusuario de Django)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role == RoleCode.SUPERADMIN)
        )
