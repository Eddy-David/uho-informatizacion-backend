"""Rutas de las integraciones institucionales (montadas en ``/api/v1/integraciones/``).

Motivo: el archivo original del kit incluía ``uho_auth.urls`` a secas en la raíz
del proyecto; aquí se expone **bajo un prefijo versionado** y solo si se activa
``UHO_KIT_ENABLED=true``, para no chocar con la autenticación JWT del SIGACU
(``/api/v1/auth/login/``).
"""

from django.urls import include, path

urlpatterns = [
    path("kit/auth/", include("apps.integraciones.kit_uho.uho_auth.urls")),
]
