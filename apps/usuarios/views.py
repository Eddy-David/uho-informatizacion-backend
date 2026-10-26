"""Vistas de autenticación y administración de usuarios."""

from __future__ import annotations

from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.usuarios.models import RoleDefinition, User
from apps.usuarios.serializers import (
    CustomTokenObtainPairSerializer,
    PasswordChangeSerializer,
    RoleDefinitionSerializer,
    UserCreateUpdateSerializer,
    UserListSerializer,
    UserSerializer,
)
from apps.usuarios.services import TIPO_USUARIO_MAP
from apps.core.constants import ADMIN_ROLES, Role
from apps.core.mixins import AuditableModelViewSet
from apps.core.permissions import IsAdmin, IsSuperAdmin


@extend_schema(
    summary="Iniciar sesión",
    description="Devuelve un par de tokens JWT (access/refresh) y los datos del usuario.",
    tags=["Autenticación"],
    responses={
        200: OpenApiResponse(description="Tokens y datos del usuario."),
        401: OpenApiResponse(description="Credenciales inválidas."),
    },
)
class LoginView(TokenObtainPairView):
    """``POST /api/v1/auth/login/`` — obtiene tokens JWT."""

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutView(APIView):
    """``POST /api/v1/auth/logout/`` — invalida el refresh token (blacklist)."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Cerrar sesión",
        request={
            "application/json": {"type": "object", "properties": {"refresh": {"type": "string"}}}
        },
        tags=["Autenticación"],
    )
    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"detail": "Debe enviar el token de refresco."}, status=400)
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response({"detail": "El token no es válido o ya fue revocado."}, status=400)
        # RF-01.5: además de invalidar la sesión local, se avisa a AGA_AUTH.
        from apps.usuarios.services import AgaAuthClient
        AgaAuthClient().logout()
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    """``GET/PATCH /api/v1/auth/me/`` — perfil del usuario autenticado."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Perfil del usuario autenticado", tags=["Autenticación"])
    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    @extend_schema(
        summary="Actualizar el perfil propio",
        request=UserSerializer,
        tags=["Autenticación"],
    )
    def patch(self, request):
        serializer = UserSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PasswordChangeView(APIView):
    """``POST /api/v1/auth/password/change/``"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Cambiar contraseña", tags=["Autenticación"])
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Contraseña actualizada correctamente."})


class UserViewSet(AuditableModelViewSet):
    """Administración de usuarios, roles y permisos (RF-08)."""

    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    search_fields = ["username", "nombres", "apellidos", "ci", "email"]
    ordering_fields = ["apellidos", "username", "fecha_alta", "last_login"]
    filterset_fields = ["role", "tipo_usuario", "campus_sede", "estado", "nivel_acceso"]
    lookup_field = "uuid"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UserCreateUpdateSerializer
        if self.action == "list":
            return UserListSerializer
        return UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.role == Role.SUPERADMIN:
            return qs
        # Los administradores normales no ven superusuarios.
        return qs.exclude(role=Role.SUPERADMIN)

    @extend_schema(summary="Estadísticas de usuarios", tags=["Usuarios y roles"])
    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        qs = self.get_queryset()
        by_role = {
            item["role"]: item["total"]
            for item in qs.values("role").annotate(total=Count("id")).order_by()
        }
        by_type = {
            item["tipo_usuario"]: item["total"]
            for item in qs.values("tipo_usuario").annotate(total=Count("id")).order_by()
        }
        return Response(
            {
                "total": qs.count(),
                "active": qs.filter(estado=True).count(),
                "by_role": by_role,
                "by_type": by_type,
            }
        )

    @extend_schema(summary="Alternar estado activo/inactivo", tags=["Usuarios y roles"])
    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, uuid=None):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response(
                {"detail": "No puede desactivar su propia cuenta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.estado = not user.estado
        user.save(update_fields=["estado"])
        return Response(UserSerializer(user).data)

    @extend_schema(summary="Restablecer contraseña", tags=["Usuarios y roles"])
    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, uuid=None):
        from apps.core.utils import generate_public_code

        user = self.get_object()
        temporary = generate_public_code(prefix="Uho", length=8)
        user.set_password(temporary)
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password"])
        return Response(
            {
                "detail": "Contraseña temporal generada. Entréguela por vía segura.",
                "temporary_password": temporary,
                "generated_at": timezone.now(),
            }
        )

    @extend_schema(summary="Roles disponibles", tags=["Usuarios y roles"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Roles del sistema y matriz de permisos", tags=["Usuarios y roles"])
    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def roles(self, request):
        from apps.usuarios.models import ROLE_MODULES

        return Response(
            [
                {
                    "value": role.value,
                    "label": str(role.label),
                    "modules": ROLE_MODULES.get(role.value, []),
                    "admin": role.value in ADMIN_ROLES,
                }
                for role in Role
            ]
        )


class AgaAuthLoginView(APIView):
    """``POST /api/v1/auth/login/aga/`` — login federado vía AGA_AUTH.

    Flujo: AgaAuthClient valida las credenciales (mock por defecto), el usuario
    local se busca o crea con ``get_or_create`` y se devuelve un par JWT.
    """

    authentication_classes: list = []  # el objetivo de la vista ES autenticar
    permission_classes: list = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        summary="Iniciar sesión vía AGA_AUTH",
        description=(
            "Autentica contra AGA_AUTH (mock en desarrollo), crea o actualiza "
            "el usuario local y devuelve tokens JWT con los datos del usuario."
        ),
        request={
            "application/json": {
                "type": "object",
                "required": ["username", "password"],
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                },
            }
        },
        tags=["Autenticación"],
        responses={
            200: OpenApiResponse(description="Tokens y datos del usuario."),
            401: OpenApiResponse(description="Credenciales rechazadas por AGA_AUTH."),
        },
    )
    def post(self, request):
        username = (request.data.get("username") or "").strip().lower()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response(
                {"detail": "Usuario y contraseña son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.usuarios.services import AgaAuthClient, AgaAuthError

        client = AgaAuthClient()
        try:
            perfil = client.authenticate(username, password)
        except AgaAuthError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        defaults = {
            "nombres": perfil.get("nombres", "")[:80],
            "apellidos": perfil.get("apellidos", "")[:120],
            "email": perfil.get("correo") or None,
            "ci": (perfil.get("dni") or "")[:11],
            "tipo_usuario": TIPO_USUARIO_MAP.get(perfil.get("tipo_usuario"), "TRABAJADOR"),
            "sync_source": "AGA_AUTH",
            "external_id": perfil.get("dni", ""),
            "last_sync_at": timezone.now(),
        }
        user, created = User.objects.get_or_create(username=username, defaults=defaults)
        if not created:
            # RF-01.3: los datos oficiales se refrescan con la respuesta de AGA_AUTH.
            for field, value in defaults.items():
                setattr(user, field, value)
            user.set_password(password)
            user.save()

        refresh = RefreshToken.for_user(user)
        refresh["username"] = user.username
        refresh["role"] = user.role
        refresh["full_name"] = user.nombre_completo
        refresh["permissions"] = user.permissions_for_ui()
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user, context={"request": request}).data,
                "aga_auth": {"modo": client.mode, "creado": created},
            }
        )


class RoleListView(APIView):
    """``GET /api/v1/auth/roles/`` — catálogo de roles y sus módulos."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Roles del sistema y matriz de permisos", tags=["Usuarios y roles"])
    def get(self, request):
        from apps.usuarios.models import ROLE_MODULES

        return Response(
            [
                {
                    "value": role.value,
                    "label": str(role.label),
                    "modules": ROLE_MODULES.get(role.value, []),
                    "admin": role.value in ADMIN_ROLES,
                }
                for role in Role
            ]
        )


class RoleDefinitionViewSet(AuditableModelViewSet):
    """CRUD de roles editables (RoleDefinition) — solo superadministradores.

    Permite listar los roles disponibles con su matriz de permisos y, desde
    la interfaz de administración, crear/ajustar roles sin modificar código.
    Los roles del sistema no se pueden eliminar (lo protege el modelo).
    """

    queryset = RoleDefinition.objects.all()
    serializer_class = RoleDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    filterset_fields = ["module", "is_active"]
    search_fields = ["code", "label", "description"]
    lookup_field = "code"

    @extend_schema(summary="Listar roles disponibles", tags=["Usuarios y roles"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
