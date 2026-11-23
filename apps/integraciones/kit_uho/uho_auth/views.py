"""Vistas del *uho-auth-kit* (login/logout con Token DRF).

IMPORTANTE — este paquete es una **referencia de integración**, no la
autenticación activa del SIGACU. La autenticación real del sistema es JWT
(``apps.usuarios.views.LoginView`` + ``apps.usuarios.services.AgaAuthClient``).

Estas vistas solo se registran en ``urls.py`` si se activa explícitamente
``UHO_KIT_ENABLED=true`` en el ``.env``; así ningún proyecto del SIGACU las
expone por accidente. Úselas si en el futuro se quiere migrar a Token DRF
(por ejemplo, para interoperar con otros proyectos de la UHO que ya usan el
kit).
"""

from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .client import uho_login

User = get_user_model()


class KitLoginView(APIView):
    """``POST`` usuario/contraseña → Token DRF.

    Flujo del kit: primero se intenta un usuario local de Django (admins,
    usuarios demo) y, si no existe, se valida contra ``auth.uho.edu.cu`` y se
    crea un usuario local sin contraseña utilizable.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        failed = Response({"error": "Login failed"}, status=status.HTTP_401_UNAUTHORIZED)

        if not username or not password:
            return failed

        # 1) Usuario local (p. ej. administradores creados en Django)
        user = authenticate(username=username, password=password)

        # 2) Si no existe localmente, validar contra la universidad
        if user is None:
            data = uho_login(username, password)
            if data is None or not data["active"]:
                return failed

            user, created = User.objects.get_or_create(
                username=data["username"] or username,
                defaults={
                    "first_name": data["name"] or "",
                    "last_name": data["surname"] or "",
                },
            )
            if created:
                user.set_unusable_password()
                user.save()

        if not user.is_active:
            return failed

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "username": user.username,
            "is_staff": user.is_staff,
        })


class KitLogoutView(APIView):
    """Elimina el Token DRF del usuario autenticado."""

    authentication_classes = [TokenAuthentication]

    def post(self, request):
        if not request.user.is_authenticated:
            raise NotAuthenticated("No authentication credentials were provided.")
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
