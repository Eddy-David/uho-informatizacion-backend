"""Configuración para desarrollo local (DEBUG activado)."""

from .base import *  # noqa: F401,F403
from .base import env_bool

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = ["*"]

# El cliente de Vite y el contenedor del frontend se ejecutan en orígenes
# distintos durante el desarrollo, por lo que CORS debe ser permisivo.
CORS_ALLOW_ALL_ORIGINS = True

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
