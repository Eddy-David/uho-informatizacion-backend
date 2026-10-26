"""Migración inicial del módulo de notificaciones."""

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("title", models.CharField(max_length=200, verbose_name="título")),
                ("message", models.TextField(verbose_name="mensaje")),
                ("category", models.CharField(choices=[("SISTEMA", "Sistema"), ("ACCESO", "Control de acceso"), ("SOLAPIN", "Solapín digital"), ("VISITA", "Visitantes"), ("VEHICULO", "Vehículos"), ("INCIDENCIA", "Incidencia"), ("SEGURIDAD", "Alerta de seguridad")], default="SISTEMA", max_length=15, verbose_name="categoría")),
                ("priority", models.CharField(choices=[("BAJA", "Baja"), ("NORMAL", "Normal"), ("ALTA", "Alta")], default="NORMAL", max_length=10, verbose_name="prioridad")),
                ("link", models.CharField(blank=True, max_length=300, verbose_name="enlace")),
                ("payload", models.JSONField(blank=True, default=dict, verbose_name="datos adicionales")),
                ("is_read", models.BooleanField(db_index=True, default=False, verbose_name="leída")),
                ("read_at", models.DateTimeField(blank=True, null=True, verbose_name="leída el")),
                ("email_sent", models.BooleanField(default=False, verbose_name="enviada por correo")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL, verbose_name="destinatario")),
            ],
            options={
                "verbose_name": "notificación",
                "verbose_name_plural": "notificaciones",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["user", "is_read"], name="idx_notification_user_read"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["-created_at"], name="idx_notification_created"),
        ),
    ]
