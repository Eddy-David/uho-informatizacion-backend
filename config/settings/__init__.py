"""Configuración por entornos del proyecto UHO SIGACU.

Módulos disponibles:

* ``base``        → ajustes compartidos (lectura del archivo ``.env``).
* ``development`` → DEBUG, recarga automática, CORS amplio.
* ``testing``     → contiene las pruebas sobre PostgreSQL y hasher rápido para CI.
* ``production``  → seguridad estricta, WhiteNoise y MinIO obligatorio.

El módulo activo se selecciona con ``DJANGO_SETTINGS_MODULE``.
"""
