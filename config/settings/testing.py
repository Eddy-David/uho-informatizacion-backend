"""Configuración para pruebas automatizadas (pytest / CI).

Las pruebas se ejecutan sobre PostgreSQL, igual que el resto de entornos: Django
crea y destruye una base de datos temporal con las credenciales del ``.env``.
"""

from .base import *  # noqa: F401,F403

DEBUG = False
TESTING = True

# PostgreSQL también en pruebas: se reutiliza la configuración de ``base`` y
# Django crea una base de datos temporal (test_uho_sigacu) por sesión de pytest.
DATABASES["default"]["TEST"] = {"NAME": env("POSTGRES_TEST_DB", "test_uho_sigacu")}  # noqa: F405

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Sin límites de peticiones ni throttling en pruebas.
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": None,
    "user": None,
    "login": None,
}

MEDIA_ROOT = BASE_DIR / "media" / "test"  # noqa: F405
