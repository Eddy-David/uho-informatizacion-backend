"""Añade ``Badge.codigo_qr`` (UUID público del QR) y el nivel PERMANENTE.

Se hace en tres pasos porque la tabla ya tiene filas:

1. Añadir el campo **sin** unicidad ni NOT NULL.
2. Rellenar con un UUID **distinto por fila**.
3. Aplicar la restricción UNIQUE + NOT NULL.
"""

import uuid

from django.db import migrations, models


def fill_codigo_qr(apps, schema_editor):
    """Asigna un UUID único a cada solapín existente."""
    Badge = apps.get_model("solapines", "Badge")
    for badge in Badge.objects.filter(codigo_qr__isnull=True).iterator():
        badge.codigo_qr = uuid.uuid4()
        badge.save(update_fields=["codigo_qr"])


class Migration(migrations.Migration):
    dependencies = [
        ("solapines", "0002_alter_badgeprintjob_total"),
    ]

    operations = [
        migrations.AddField(
            model_name="badge",
            name="codigo_qr",
            field=models.UUIDField(
                null=True,
                editable=False,
                db_index=True,
                verbose_name="código QR",
            ),
        ),
        migrations.RunPython(fill_codigo_qr, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="badge",
            name="codigo_qr",
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                db_index=True,
                verbose_name="código QR",
            ),
        ),
        migrations.AlterField(
            model_name="badge",
            name="access_level",
            field=models.CharField(
                choices=[
                    ("LIBRE", "Acceso libre"),
                    ("PERMANENTE", "Acceso permanente"),
                    ("LIMITADO", "Acceso limitado"),
                    ("RESTRINGIDO", "Acceso restringido"),
                    ("ESTUDIANTE", "Estudiante"),
                    ("VISITANTE", "Visitante"),
                ],
                default="LIMITADO",
                max_length=20,
                verbose_name="nivel de acceso",
            ),
        ),
    ]
