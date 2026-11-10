"""``python manage.py generar_accesos_demo`` — datos masivos de prueba (RF-08.5).

Genera entre 150 y 200 registros en la bitácora de accesos para poblar las
gráficas del dashboard en la demostración. Borra primero los registros demo
anteriores (identificados por la observación DEMO) sin tocar los reales.

Uso::

    python manage.py generar_accesos_demo            # ~175 registros para hoy
    python manage.py generar_accesos_demo --total 200
"""

from __future__ import annotations

import random
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.access_control.models import AccessLog
from apps.core.catalogs import AccessPoint
from apps.core.constants import Campus, MovementType, UserType

#: Observación que marca un registro como dato de demostración.
DEMO_MARKER = "DEMO"

#: Curva realista de afluencia (7:00 a 18:00) con picos de entrada y salida.
HORA_PESOS = {
    7: 10, 8: 22, 9: 14, 10: 10, 11: 9, 12: 8,
    13: 6, 14: 10, 15: 12, 16: 9, 17: 6, 18: 4,
}


class Command(BaseCommand):
    help = "Genera datos masivos de prueba para las gráficas del dashboard (RF-08.5)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            type=int,
            default=None,
            help="Cantidad exacta de registros a generar (150-200).",
        )

    def handle(self, *args, **options):
        total = options["total"]
        if total is None:
            total = random.randint(150, 200)
        total = max(1, min(total, 200))

        with transaction.atomic():
            borrados = self._limpiar_demo()
            creados = self._generar(total)

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {borrados} registros demo eliminados, {creados} creados para hoy."
        ))

    # ------------------------------------------------------------------ pasos
    def _limpiar_demo(self) -> int:
        """Elimina solo los accesos marcados como demo; los reales no se tocan."""
        count, _ = AccessLog.objects.filter(observed=DEMO_MARKER).delete()
        return count

    def _generar(self, total: int) -> int:
        rnd = random.Random()
        usuarios = self._usuarios_por_tipo()
        if not usuarios:
            self.stdout.write(self.style.WARNING(
                "No hay usuarios en la base de datos: todos los registros serán anónimos."
            ))
        puntos = list(AccessPoint.objects.all())

        # Reparto con variedad: estudiantes dominan (como en una universidad real).
        tipos = [UserType.STUDENT] * 5 + [UserType.WORKER] * 3 + [UserType.TEACHER] * 2
        tipos += [UserType.MANAGER, UserType.VISITOR]
        sedes = [Campus.CENTRAL, Campus.PIEDRA_BLANCA, Campus.PEDAGOGICA, Campus.CULTURA_FISICA]
        horas = list(HORA_PESOS.keys())
        pesos = list(HORA_PESOS.values())

        lote = []
        for _ in range(total):
            tipo = rnd.choice(tipos)
            user = rnd.choice(usuarios.get(tipo, [None]))
            campus = rnd.choice(sedes)
            punto = rnd.choice(puntos) if puntos else None
            hora = rnd.choices(horas, weights=pesos)[0]
            occurred = timezone.localtime().replace(
                hour=hora,
                minute=rnd.randint(0, 59),
                second=rnd.randint(0, 59),
                microsecond=0,
            )
            # Salidas más probables por la tarde; entradas por la mañana.
            movement = (
                MovementType.ENTRY if hora < 13 and rnd.random() < 0.7
                else MovementType.EXIT if hora >= 13 and rnd.random() < 0.7
                else rnd.choice([MovementType.ENTRY, MovementType.EXIT])
            )
            # ~7% denegados para simular incidencias.
            denied = rnd.random() < 0.07
            lote.append(AccessLog(
                user=user,
                full_name=user.nombre_completo if user else "Visitante Demo",
                identity_card=user.ci if user else "",
                user_type=tipo,
                campus=campus,
                access_point=punto,
                movement=movement,
                result=AccessLog.Result.DENIED if denied else AccessLog.Result.GRANTED,
                denial_reason=rnd.choice([
                    "Solapín vencido", "Zona restringida", "Solapín suspendido",
                ]) if denied else "",
                occurred_at=occurred,
                observed=DEMO_MARKER,
            ))
        AccessLog.objects.bulk_create(lote)
        return len(lote)

    @staticmethod
    def _usuarios_por_tipo() -> dict[str, list]:
        """Agrupa usuarios activos por ``tipo_usuario`` para variedad en el pastel."""
        from apps.usuarios.models import User

        resultado: dict[str, list] = {}
        for user in User.objects.filter(estado=True).iterator():
            resultado.setdefault(user.tipo_usuario, []).append(user)
        return resultado
