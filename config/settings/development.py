"""Configuración para desarrollo local (DEBUG activado)."""

import os
from urllib.parse import urlparse

from .base import *  # noqa: F401,F403
from .base import env_bool, env_list

DEBUG = env_bool("DJANGO_DEBUG", True)


def _tunnel_hosts(*variables: str) -> list[str]:
    """Hosts de los túneles de desarrollo (localtunnel/ngrok) activos.

    Se leen de variables de entorno para no tener que editar este archivo cada
    vez que el túnel cambia de subdominio. `scripts/tunel.sh` las define y
    reinicia el backend automáticamente:

    * ``TUNNEL_BACKEND_URL``  → host público del backend (Django).
      Debe estar en ``ALLOWED_HOSTS`` para que Django no responda 400
      ("Invalid HTTP_HOST header") a las peticiones del móvil.
    * ``TUNNEL_FRONTEND_URL`` → origen público del frontend (Vite). El móvil
      entra por ese HTTPS y la API se llama con ruta relativa `/api/v1`, que
      Vite reenvía al backend: **no** hay origen cruzado en el túnel, y por eso
      CORS/CSRF no necesitan nada extra. Se declara igualmente para que el
      panel de administración y los WebSockets abiertos desde el túnel pasen
      las validaciones de origen. `scripts/tunel.sh` la exporta.

    Acepta ``https://host``, ``host`` o ``https://host/`` indistintamente y
    descarta valores vacíos: sin túneles, ambas listas quedan como antes.
    """
    hosts: list[str] = []
    for variable in variables:
        valor = os.environ.get(variable, "").strip()
        if not valor:
            continue
        if "://" not in valor:
            valor = f"https://{valor}"
        host = urlparse(valor).hostname or ""
        if host and host not in hosts:
            hosts.append(host)
    return hosts


ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    # IP de la laptop en la red local (acceso desde el móvil por WiFi).
    "192.168.1.27",
    # Alias del contenedor backend en Docker Compose.
    "backend",
    # Túneles HTTPS de desarrollo (sólo si están configurados; sin túneles la
    # lista queda igual que antes).
    *_tunnel_hosts("TUNNEL_BACKEND_URL", "TUNNEL_FRONTEND_URL"),
]

# El cliente de Vite y el contenedor del frontend se ejecutan en orígenes
# distintos durante el desarrollo, por lo que CORS debe ser permisivo.
# Se puede restringir con CORS_ALLOW_ALL_ORIGINS=false en .env o al arrancar.
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", True)

# Orígenes explícitos permitidos: navegador local y móvil en la red WiFi.
# `CORS_ALLOW_ALL_ORIGINS` ya los cubre, pero se declaran para que funcione
# igual si esa opción se desactiva con `CORS_ALLOW_ALL_ORIGINS=false`.
CORS_ALLOWED_ORIGINS = [
    # Vite sirve el frontend por HTTP estándar (runserver no soporta HTTPS).
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Acceso desde el móvil por la IP de la red local.
    "http://192.168.1.27:5173",
    "http://192.168.1.27:5174",
    # Orígenes extra (p. ej. un túnel fijo de ngrok): lista separada por comas.
    # `scripts/tunel.sh` exporta TUNNEL_FRONTEND_URL, que se añade aquí abajo.
    *env_list("SIGACU_EXTRA_CORS_ORIGINS", ""),
    # El frontend del móvil corre en el túnel (https://yyyy.loca.lt).
    # La API se consume con ruta relativa por el proxy de Vite, así que esto
    # sólo cubre llamadas de origen cruzado directas al túnel del backend.
    *(
        f"https://{h}"
        for h in _tunnel_hosts("TUNNEL_FRONTEND_URL", "TUNNEL_BACKEND_URL")
        if "localhost" not in h
    ),
]

# CSRF: necesario si el móvil usa el panel de administración de Django.
# Django exige el prefijo del esquema en cada origen; en desarrollo todo va por HTTP.
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.1.27:5173",
    "http://192.168.1.27:5174",
    "http://localhost:8000",
    "http://192.168.1.27:8000",
    *env_list("SIGACU_EXTRA_CSRF_ORIGINS", ""),
    # Origen HTTPS del túnel del frontend (scripts/tunel.sh) y del backend si
    # alguna vez se expone por separado (SIGACU_EXTRA_CSRF_ORIGINS).
    *(
        f"https://{h}"
        for h in _tunnel_hosts("TUNNEL_FRONTEND_URL", "TUNNEL_BACKEND_URL")
        if "localhost" not in h
    ),
]

# Desarrollo por HTTP: no se fuerza la redirección a HTTPS ni se marcan las
# cookies como Secure. `SECURE_SSL_REDIRECT = True` dejaría el backend
# inalcanzable desde Vite (bucle de redirección).
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)

# WebSockets (Channels): el origen que valida `AllowedHostsOriginValidator`
# del ASGI es el del frontend, ya cubierto por ALLOWED_HOSTS de arriba (incluido
# el host del túnel cuando `TUNNEL_FRONTEND_URL` está definido).

# Channels en memoria por defecto: no requiere Redis para `runserver`.
if not env_bool("USE_REDIS_CHANNEL_LAYER", False):
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }

# Almacenamiento local mientras MinIO no esté disponible.
if not env_bool("USE_MINIO", False):
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# En desarrollo se permite navegar el API schema sin autenticación.
REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = (  # noqa: F405
    "rest_framework.permissions.IsAuthenticated",
)



INTERNAL_IPS = ["127.0.0.1", "localhost"]
