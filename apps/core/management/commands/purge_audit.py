"""``python manage.py purge_audit`` — aplica la política de retención.

Los eventos de auditoría son inmutables por la API, pero la política
institucional exige una retención máxima. Este comando es el **único**
mecanismo permitido para eliminarlos, y registra el propio purgado.

Uso::

    python manage.py purge_audit                 # retención por defecto (730 días)
    python manage.py purge_audit --days 1095     # 3 años
    python manage.py purge_audit --dry-run       # solo cuenta
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from apps.core.audit import AuditEvent, audit_event


class Command(BaseCommand):
    help = "Elimina eventos de auditoría anteriores al período de retención."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=730, help="Días de retención (por defecto 730)."
        )
        parser.add_argument("--dry-run", action="store_true", help="Solo informa, no elimina.")

    def handle(self, *args, **options):
        days = options["days"]
        cutoff = timezone.now() - timedelta(days=days)
        queryset = AuditEvent.objects.filter(created_at__lt=cutoff)
        total = queryset.count()

        self.stdout.write(f"Eventos anteriores a {cutoff:%Y-%m-%d} ({days} días): {total}")
        if options["dry_run"] or total == 0:
            self.stdout.write(self.style.WARNING("Modo simulación: no se eliminó ningún registro."))
            return

        # Borrado físico en bloque: ``delete()`` está bloqueado por diseño.
        table = AuditEvent._meta.db_table  # noqa: SLF001
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {table} WHERE created_at < %s", [cutoff])

        audit_event(
            action=AuditEvent.Action.OTHER,
            module="audit",
            description=f"Purga de auditoría: {total} eventos anteriores a {cutoff:%Y-%m-%d}",
            metadata={"dias_retencion": days, "eliminados": total},
            severity=AuditEvent.Severity.WARNING,
        )
        self.stdout.write(self.style.SUCCESS(f"Eliminados {total} eventos de auditoría."))
