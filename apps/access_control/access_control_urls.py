"""Rutas del motor de verificación y registro de acceso (RF-04).

Prefijo oficial: ``/api/v1/access_control/``

* ``POST verify/``   → ejecuta el motor y responde con ``permitido``/``razon``.
* ``POST register/`` → registra el movimiento en la bitácora.
"""

from django.urls import path

from apps.access_control.views import AccessLogViewSet, VerifyAccessControlView

app_name = "access_control_api"

_register = AccessLogViewSet.as_view({"post": "register"})

urlpatterns = [
    path("verify/", VerifyAccessControlView.as_view(), name="verify"),
    path("register/", _register, name="register"),
]
