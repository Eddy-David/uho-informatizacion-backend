"""Serializers de autenticación y usuarios."""

from __future__ import annotations
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.usuarios.constants import ALL_PERMISSIONS, RoleCode
from apps.usuarios.models import RoleDefinition, User
class UserPublicSerializer(serializers.ModelSerializer):
    """Datos públicos del usuario; los alias en inglés son de solo lectura."""

    full_name = serializers.CharField(source="nombre_completo", read_only=True)
    identity_card = serializers.CharField(read_only=True)
    photo = serializers.ImageField(source="foto", read_only=True)
    user_type = serializers.CharField(source="tipo_usuario", read_only=True)
    campus = serializers.CharField(source="campus_sede", read_only=True)
    position = serializers.CharField(source="cargo", read_only=True)
    access_level = serializers.CharField(source="nivel_acceso", read_only=True)
    is_active = serializers.BooleanField(source="estado", read_only=True)
    date_joined = serializers.DateTimeField(source="fecha_alta", read_only=True)


class UserSerializer(UserPublicSerializer):
    """Representación pública del usuario (usada por ``/auth/me/``)."""

    initials = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    user_type_display = serializers.CharField(source="get_tipo_usuario_display", read_only=True)
    access_level_display = serializers.CharField(source="get_nivel_acceso_display", read_only=True)
    permissions = serializers.SerializerMethodField()
    extra_permissions = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "uuid",
            "username",
            "email",
            "nombres",
            "apellidos",
            "nombre_completo",
            # Alias en inglés: los consume el frontend existente.
            "full_name",
            "initials",
            "extra_permissions",
            "ci",
            "identity_card",
            "birth_date",
            "sex",
            "phone",
            "foto",
            "photo",
            "tipo_usuario",
            "user_type",
            "user_type_display",
            "area",
            "cargo",
            "position",
            "facultad",
            "carrera",
            "ano",
            "estado",
            "is_active",
            "role",
            "role_display",
            "campus_sede",
            "campus",
            "nivel_acceso",
            "access_level",
            "access_level_display",
            "fecha_alta",
            "date_joined",
            "last_login",
            "permissions",
        )

    def get_permissions(self, obj) -> list[str]:
        return obj.permissions_for_ui()


class UserListSerializer(UserPublicSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "uuid",
            "username",
            "nombres",
            "apellidos",
            "nombre_completo",
            "full_name",
            "ci",
            "identity_card",
            "email",
            "role",
            "role_display",
            "tipo_usuario",
            "user_type",
            "campus_sede",
            "campus",
            "area",
            "cargo",
            "position",
            "facultad",
            "carrera",
            "ano",
            "nivel_acceso",
            "access_level",
            "estado",
            "is_active",
            "last_login",
        )


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    extra_permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=sorted(ALL_PERMISSIONS)),
        required=False,
        default=list,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "uuid",
            "username",
            "email",
            "nombres",
            "apellidos",
            "ci",
            "birth_date",
            "sex",
            "phone",
            "foto",
            "tipo_usuario",
            "role",
            "campus_sede",
            "area",
            "cargo",
            "facultad",
            "carrera",
            "ano",
            "nivel_acceso",
            "estado",
            "password",
            "extra_permissions",
        )
        read_only_fields = ("id", "uuid")

    def validate_ci(self, value):
        value = (value or "").strip()
        if value and not value.isdigit():
            raise serializers.ValidationError("El carnet de identidad debe contener solo dígitos.")
        if value and len(value) != 11:
            raise serializers.ValidationError("El carnet de identidad debe tener 11 dígitos.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.user and request.user.role != RoleCode.SUPERADMIN:
            requested_role = attrs.get("role")
            if requested_role in (RoleCode.SUPERADMIN, RoleCode.ADMIN):
                raise serializers.ValidationError(
                    {"role": "Solo un superadministrador puede asignar este rol."}
                )
            # Un administrador no puede conceder permisos puntuales.
            if attrs.get("extra_permissions"):
                raise serializers.ValidationError(
                    {
                        "extra_permissions": "Solo un superadministrador puede conceder permisos adicionales."
                    }
                )
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "La contraseña es obligatoria."})
        return attrs

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
            instance.must_change_password = False
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """Credenciales de acceso.

    Se define explícitamente para documentar el contrato en Swagger y para
    personalizar los mensajes de error.
    """

    username = serializers.CharField(help_text="Usuario de red UHO (ej. lourdes.columbie)")
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    default_error_messages = {
        "invalid_credentials": "Credenciales inválidas o cuenta deshabilitada.",
        "inactive_account": "La cuenta está deshabilitada.",
    }

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(
            request=request,
            username=attrs["username"].strip().lower(),
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError(
                {"detail": self.error_messages["invalid_credentials"]}, code="invalid_credentials"
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": self.error_messages["inactive_account"]}, code="inactive_account"
            )
        attrs["user"] = user
        return attrs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Añade datos del usuario y permisos al token de acceso."""

    default_error_messages = {
        "no_active_account": "Las credenciales no son válidas o la cuenta está inactiva."
    }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        token["full_name"] = user.nombre_completo
        token["permissions"] = user.permissions_for_ui()
        return token

    def validate(self, attrs):
        username = (attrs.get("username") or "").strip().lower()
        candidate = User.objects.filter(username=username).first()
        if candidate is not None and candidate.is_locked:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "La cuenta está bloqueada temporalmente por intentos fallidos. "
                        "Intente de nuevo más tarde."
                    )
                },
                code="account_locked",
            )

        try:
            data = super().validate(attrs)
        except Exception:
            if candidate is not None:
                candidate.register_failed_login()
                self._audit("LOGIN_FAILED", candidate, reason="Credenciales inválidas")
            raise

        self._audit("LOGIN_SUCCESS", self.user)
        request = self.context.get("request")
        if request is not None:
            from apps.core.audit import update_context
            from apps.core.utils import client_ip

            user = self.user
            user.last_login_ip = client_ip(request)
            user.reset_failed_login()
            user.save(update_fields=["last_login_ip"])

            # Deja al usuario en el contexto de auditoría para que el
            # LogAuditoria del middleware quede vinculado a la cuenta autenticada.
            update_context(user=user)

        data["user"] = UserSerializer(self.user).data
        return data

    @staticmethod
    def _audit(action: str, user, reason: str = "") -> None:
        """Registra el intento de autenticación (no interrumpe el login si falla)."""
        try:
            from apps.core.audit import audit_event

            audit_event(
                action=action,
                module="auth",
                actor=user if action == "LOGIN_SUCCESS" else None,
                target_type="User",
                target_id=str(user.uuid),
                target_repr=user.username,
                metadata={"motivo": reason} if reason else {},
            )
        except Exception:  # pragma: no cover - la auditoría nunca rompe la autenticación
            pass


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        return user


class NotificationPreferenceSerializer(serializers.Serializer):
    """Preferencias de notificación (base para el módulo RF-10)."""

    email = serializers.BooleanField(default=True)
    websocket = serializers.BooleanField(default=True)
    security_alerts = serializers.BooleanField(default=True)

    def update(self, instance, validated_data):
        return validated_data


class AdminUserStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    by_role = serializers.DictField(child=serializers.IntegerField())
    by_type = serializers.DictField(child=serializers.IntegerField())


# ---------------------------------------------------------------------------
# Roles y permisos
# ---------------------------------------------------------------------------
class RoleDefinitionSerializer(serializers.ModelSerializer):
    """Rol con su matriz de permisos (gestión por superadministradores)."""

    user_count = serializers.SerializerMethodField()
    module_display = serializers.CharField(source="get_module_display", read_only=True)

    class Meta:
        model = RoleDefinition
        fields = (
            "id",
            "code",
            "label",
            "description",
            "module",
            "module_display",
            "permissions",
            "is_active",
            "is_system",
            "sort_order",
            "user_count",
            "updated_at",
        )
        read_only_fields = ("id", "code", "is_system", "sort_order", "updated_at")

    def get_user_count(self, obj) -> int:
        from apps.usuarios.models import User

        return User.objects.filter(role=obj.code, estado=True).count()

    def validate_permissions(self, value):
        invalid = [p for p in value or [] if p != "*" and p not in ALL_PERMISSIONS]
        if invalid:
            raise serializers.ValidationError(f"Permisos no válidos: {', '.join(invalid)}")
        if "*" in value and len(value) > 1:
            raise serializers.ValidationError("El comodín '*' no se combina con otros permisos.")
        return sorted(set(value))

    def validate(self, attrs):
        instance = self.instance
        if instance and instance.code == RoleCode.SUPERADMIN and "permissions" in attrs:
            if attrs["permissions"] != ["*"]:
                raise serializers.ValidationError(
                    {
                        "permissions": "El rol Superadministrador debe conservar el acceso total ('*')."
                    }
                )
        return attrs


class PermissionItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    action = serializers.CharField()
    label = serializers.CharField()


class PermissionGroupSerializer(serializers.Serializer):
    resource = serializers.CharField()
    permissions = PermissionItemSerializer(many=True)


class GrantPermissionsSerializer(serializers.Serializer):
    """Concesión puntual de permisos a un usuario (solo SA)."""

    extra_permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=sorted(ALL_PERMISSIONS)),
        allow_empty=True,
    )
