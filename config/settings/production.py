"""Configuración de producción (endurecida).

Se activa con ``DJANGO_SETTINGS_MODULE=config.settings.production``.
Requiere valores reales de DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS,
CORS_ALLOWED_ORIGINS y credenciales de PostgreSQL/MinIO.
"""

from .base import *  # noqa: F401,F403
from .base import env, env_bool, env_list

DEBUG = False
TESTING = False

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost")

if SECRET_KEY == "django-insecure-change-me-in-production":  # noqa: F405
    raise RuntimeError(
        "DJANGO_SECRET_KEY no está configurada. Defina una clave segura en .env "
        "antes de iniciar en producción."
    )

# --- Seguridad HTTP ---------------------------------------------------------
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_BROWSER_XSS_FILTER = True

SESSION_COOKIE_SECURE = env_bool(
    "SESSION_COOKIE_SECURE", False if SECURE_SSL_REDIRECT is False else True
)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"

# --- Correo -----------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")

# --- Canales: Redis obligatorio en producción ------------------------------
if env_bool("USE_IN_MEMORY_CHANNEL_LAYER", False):
    raise RuntimeError("El canal en memoria no está permitido en producción.")

# --- Registro en consola (Docker recoge stdout) -----------------------------
LOGGING["handlers"]["console"]["formatter"] = "verbose"  # noqa: F405
