"""
UHO SIGACU — Configuración base compartida por todos los entornos.

Sistema de Desarrollo para el Proceso de Informatización de la
Universidad de Holguín "Oscar Lucero Moya" (UHO).

Todas las variables sensibles se leen del archivo ``.env`` ubicado en la raíz
del repositorio (o se inyectan como variables de entorno en Docker). Consulte
``.env.example`` para el catálogo completo de variables.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Rutas del proyecto
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_ROOT = BASE_DIR.parent  # raíz del repositorio

# Se cargan primero el .env de la raíz (compartido con Docker Compose) y
# después el .env propio del backend, si existe (este último tiene prioridad).
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(BASE_DIR / ".env", override=True)


# ---------------------------------------------------------------------------
# Utilidades de lectura de variables
# ---------------------------------------------------------------------------
def env(key: str, default: str = "") -> str:
    """Devuelve una variable de entorno como cadena."""
    return os.getenv(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    """Interpreta variables de entorno con valores tipo booleano."""
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def env_int(key: str, default: int = 0) -> int:
    """Interpreta variables de entorno numéricas enteras."""
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def env_list(key: str, default: str = "") -> list[str]:
    """Convierte una lista separada por comas en una lista de cadenas."""
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Núcleo de Django
# ---------------------------------------------------------------------------
DJANGO_ENV = env("DJANGO_ENV", "development")
SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-change-me-in-production")

DEBUG = env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    # Aplicaciones de Channels (deben ir antes de staticfiles)
    "daphne",
    # Núcleo
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "oauth2_provider",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "channels",
    "storages",
    # Aplicaciones del proyecto
    "apps.core",
    "apps.auditoria",
    "apps.usuarios",
    "apps.access_control",
    "apps.solapines",
    "apps.visitors",
    "apps.vehicles",
    "apps.incidents",
    "apps.notifications",
    "apps.reports",
    # Módulos universitarios futuros (RF-11 … RF-15) — esqueleto expandible
    "apps.students",
    "apps.academic",
    "apps.hr",
    "apps.maintenance",
    "apps.research",
    "apps.analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Auditoría transversal (ID de correlación, contexto, trazas y LogAuditoria)
    "apps.core.middleware.RequestAuditMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Base de datos PostgreSQL
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "uho_sigacu"),
        "USER": env("POSTGRES_USER", "uho_sigacu"),
        "PASSWORD": env("POSTGRES_PASSWORD", "uho_sigacu"),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": env_int("POSTGRES_CONN_MAX_AGE", 60),
        "OPTIONS": {
            "connect_timeout": env_int("POSTGRES_CONNECT_TIMEOUT", 10),
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Usuario personalizado y contraseñas
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "usuarios.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": env_int("PASSWORD_MIN_LENGTH", 8)},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_RESET_TIMEOUT = 60 * 60 * 24  # 24 horas


# ---------------------------------------------------------------------------
# Internacionalización (Cuba)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = env("LANGUAGE_CODE", "es")  # ``es-CU`` si se carga el locale cubano
TIME_ZONE = env("TIME_ZONE", "America/Havana")
USE_I18N = True
USE_L10N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Archivos estáticos y medios
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsPagination",
    "PAGE_SIZE": env_int("API_PAGE_SIZE", 20),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", "60/hour"),
        "user": env("THROTTLE_USER", "2000/hour"),
        "login": env("THROTTLE_LOGIN", "10/minute"),
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
}


# ---------------------------------------------------------------------------
# JWT (Simple JWT)
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 60)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7)),
    "ROTATE_REFRESH_TOKENS": env_bool("JWT_ROTATE_REFRESH_TOKENS", True),
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.usuarios.serializers.CustomTokenObtainPairSerializer",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}


# ---------------------------------------------------------------------------
# OAuth2 (django-oauth-toolkit) — listo para SSO institucional
# ---------------------------------------------------------------------------
OAUTH2_PROVIDER = {
    "SCOPES": {
        "read": "Lectura de datos",
        "write": "Escritura de datos",
        "openid": "Identidad del usuario (OpenID Connect)",
    },
    "ACCESS_TOKEN_EXPIRE_SECONDS": env_int("OAUTH2_ACCESS_TOKEN_EXPIRE_SECONDS", 3600),
    "REFRESH_TOKEN_EXPIRE_SECONDS": env_int("OAUTH2_REFRESH_TOKEN_EXPIRE_SECONDS", 604800),
    "OIDC_ENABLED": env_bool("OAUTH2_OIDC_ENABLED", False),
    "PKCE_REQUIRED": False,
}


# ---------------------------------------------------------------------------
# CORS / CSRF
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)


# ---------------------------------------------------------------------------
# Canales / WebSockets
# ---------------------------------------------------------------------------
# Redis como canal de comunicación entre procesos. Si no hay Redis disponible
# se usa InMemoryChannelLayer (solo válido para un único proceso de desarrollo).
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/1")

if env_bool("USE_IN_MEMORY_CHANNEL_LAYER", False):
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }


# ---------------------------------------------------------------------------
# Celery (opcional)
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/2")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://localhost:6379/3")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE


# ---------------------------------------------------------------------------
# Almacenamiento de archivos en MinIO (S3 compatible)
# ---------------------------------------------------------------------------
USE_MINIO = env_bool("USE_MINIO", False)

# En producción el entorno Docker activa MinIO de forma obligatoria.
if DJANGO_ENV == "production" and not env_bool("ALLOW_LOCAL_MEDIA", False):
    USE_MINIO = True

MINIO_ENDPOINT = env("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = env("MINIO_ACCESS_KEY", env("MINIO_ROOT_USER", "minioadmin"))
MINIO_SECRET_KEY = env("MINIO_SECRET_KEY", env("MINIO_ROOT_PASSWORD", "minioadmin"))
MINIO_BUCKET_NAME = env("MINIO_BUCKET_NAME", "uho-sigacu-media")
MINIO_PUBLIC_BUCKET_NAME = env("MINIO_PUBLIC_BUCKET_NAME", "uho-sigacu-public")
MINIO_USE_SSL = env_bool("MINIO_USE_SSL", False)
MINIO_DEFAULT_ACL = env("MINIO_DEFAULT_ACL", "private")
# Las URLs firmadas deben ser accesibles desde el navegador del usuario:
# dentro de Docker la API usa http://minio:9000, pero el cliente necesita
# http://localhost:9000 (o el dominio público).
MINIO_PUBLIC_ENDPOINT = env("MINIO_PUBLIC_ENDPOINT", MINIO_ENDPOINT)

if USE_MINIO:
    AWS_ACCESS_KEY_ID = MINIO_ACCESS_KEY
    AWS_SECRET_ACCESS_KEY = MINIO_SECRET_KEY
    AWS_STORAGE_BUCKET_NAME = MINIO_BUCKET_NAME
    AWS_S3_ENDPOINT_URL = MINIO_ENDPOINT
    AWS_S3_CUSTOM_DOMAIN = env("MINIO_CUSTOM_DOMAIN", "")
    AWS_S3_ADDRESSING_STYLE = env("MINIO_ADDRESSING_STYLE", "path")
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_REGION_NAME = env("MINIO_REGION", "us-east-1")
    AWS_S3_USE_SSL = MINIO_USE_SSL
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = env_int("MINIO_SIGNED_URL_EXPIRE", 3600)
    AWS_S3_FILE_OVERWRITE = False

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }


# Si se desactiva el almacenamiento comprimido con manifiesto, se sirven los
# estáticos originales (útil en desarrollo cuando cambia el CSS con frecuencia).
if not env_bool("STATICFILES_HASHED", True):
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}


# ---------------------------------------------------------------------------
# Documentación OpenAPI (Swagger UI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "UHO SIGACU API",
    "DESCRIPTION": (
        "API REST del Sistema de Desarrollo para el Proceso de Informatización "
        "de la Universidad de Holguín. Incluye autenticación JWT, gestión de "
        "usuarios y roles, control de acceso, solapín digital, visitantes, "
        "vehículos, incidencias y reportes."
    ),
    "VERSION": env("APP_VERSION", "1.0.0"),
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "SORT_OPERATIONS": False,
    "TAGS": [
        {"name": "Autenticación", "description": "Login, refresh, logout y perfil."},
        {"name": "Catálogos", "description": "Nomencladores del sistema."},
        {"name": "Usuarios y roles", "description": "Gestión de cuentas y permisos."},
        {"name": "Control de acceso", "description": "Verificación y bitácora."},
        {"name": "Solapín digital", "description": "Plantillas, credenciales y QR."},
        {"name": "Visitantes", "description": "Solicitudes de visita y aprobación."},
        {"name": "Vehículos", "description": "Catálogo y movimientos vehiculares."},
        {"name": "Incidencias", "description": "Registro y seguimiento."},
        {"name": "Notificaciones", "description": "Centro de notificaciones y WebSockets."},
        {"name": "Reportes", "description": "Indicadores, PDF y Excel."},
    ],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
    },
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "jwtAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "tokenUrl": "/api/v1/auth/token/",
                        "scopes": {"read": "Lectura", "write": "Escritura"},
                    }
                },
            },
        }
    },
}


# ---------------------------------------------------------------------------
# Integraciones institucionales (Cuban university infrastructure)
# ---------------------------------------------------------------------------
# AGA_AUTH: autenticación contra el dominio de red de la UHO.
# SIGENU:   nomenclador de estudiantes / trabajadores.
# ASSET:    inventario institucional.
# Las integraciones se activan con *_ENABLED=True; mientras estén desactivadas
# el sistema usa autenticación local (tabla de usuarios de Django).
UHO_INTEGRATIONS = {
    "AGA_AUTH": {
        "enabled": env_bool("AGA_AUTH_ENABLED", False),
        "base_url": env("AGA_AUTH_BASE_URL", ""),
        "timeout": env_int("AGA_AUTH_TIMEOUT", 5),
    },
    "SIGENU": {
        "enabled": env_bool("SIGENU_ENABLED", False),
        "base_url": env("SIGENU_BASE_URL", ""),
        "token": env("SIGENU_TOKEN", ""),
        "timeout": env_int("SIGENU_TIMEOUT", 5),
    },
    "ASSET": {
        "enabled": env_bool("ASSET_ENABLED", False),
        "base_url": env("ASSET_BASE_URL", ""),
        "token": env("ASSET_TOKEN", ""),
        "timeout": env_int("ASSET_TIMEOUT", 5),
    },
}


# ---------------------------------------------------------------------------
# Registro de eventos y correo
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {process:d} {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {asctime} {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {
            "handlers": ["console"],
            "level": env("APP_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "sigacu@uho.edu.cu")


# ---------------------------------------------------------------------------
# Auditoría transversal
# ---------------------------------------------------------------------------
# Días de retención antes de permitir ``manage.py purge_audit``.
AUDIT_RETENTION_DAYS = env_int("AUDIT_RETENTION_DAYS", 730)
# Solo se auditan automáticamente los modelos marcados con ``AuditedModel``.
AUDIT_ENABLED = env_bool("AUDIT_ENABLED", True)

# ---------------------------------------------------------------------------
# Integración AGA_AUTH (autenticación centralizada)
# ---------------------------------------------------------------------------
# ``mock``  → desarrollo: acepta cualquier usuario/contraseña no vacíos.
# ``real``  → producción: pendiente de implementar (AgaAuthClient._authenticate_remote).
AGA_AUTH_MODE = env("AGA_AUTH_MODE", "mock")


# ---------------------------------------------------------------------------
# Metadatos institucionales usados en PDF y frontend
# ---------------------------------------------------------------------------
INSTITUTION_NAME = env("INSTITUTION_NAME", "Universidad de Holguín Oscar Lucero Moya")
INSTITUTION_SHORT_NAME = env("INSTITUTION_SHORT_NAME", "UHO")
APP_NAME = env("VITE_APP_NAME", "SIGACU")
APP_VERSION = env("APP_VERSION", "1.0.0")
