"""Configuración de Celery (tareas asíncronas).

El proyecto incluye Celery como punto de extensión para tareas programadas
(sincronización con AGA_AUTH, SIGENU y ASSET, envío diferido de notificaciones,
generación masiva de solapines). No se requiere un worker para el
funcionamiento básico del sistema.

Uso en un futuro worker:

    celery -A config worker -l info
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("uho_sigacu")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de diagnóstico usada para comprobar que el worker responde."""
    return f"Celery OK: {self.request!r}"
