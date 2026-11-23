"""Rutas opcionales del *uho-auth-kit*.

Se incluyen en el proyecto solo cuando ``UHO_KIT_ENABLED=true`` (ver
``apps.integraciones.kit_uho.urls``). Con ese flag activo quedan publicadas en::

    /api/v1/integraciones/kit/auth/login/
    /api/v1/integraciones/kit/auth/logout/
"""

from django.urls import path

from .views import KitLoginView, KitLogoutView

app_name = "kit_uho_auth"

urlpatterns = [
    path("login/", KitLoginView.as_view(), name="login"),
    path("logout/", KitLogoutView.as_view(), name="logout"),
]
