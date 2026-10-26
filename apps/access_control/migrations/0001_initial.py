"""Migración inicial de la bitácora de accesos."""

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("usuarios", "0001_initial"),
        ("core", "0001_initial"),
        ("solapines", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("full_name", models.CharField(blank=True, max_length=200, verbose_name="nombre completo")),
                ("identity_card", models.CharField(blank=True, max_length=20, verbose_name="CI / pasaporte")),
                ("user_type", models.CharField(blank=True, max_length=30, verbose_name="tipo de usuario")),
                ("access_level", models.CharField(blank=True, max_length=20, verbose_name="nivel de acceso")),
                ("campus", models.CharField(blank=True, max_length=20, verbose_name="sede")),
                ("movement", models.CharField(choices=[("ENTRADA", "Entrada"), ("SALIDA", "Salida")], default="ENTRADA", max_length=10, verbose_name="movimiento")),
                ("result", models.CharField(choices=[("PERMITIDO", "Permitido"), ("DENEGADO", "Denegado")], max_length=20, verbose_name="resultado")),
                ("denial_reason", models.CharField(blank=True, max_length=120, verbose_name="motivo de denegación")),
                ("channel", models.CharField(choices=[("WEB", "Web"), ("PWA", "App / PWA"), ("MANUAL", "Manual")], default="WEB", max_length=10, verbose_name="canal")),
                ("observed", models.CharField(blank=True, max_length=255, verbose_name="observaciones")),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name="ocurrido el")),
                ("synced_at", models.DateTimeField(blank=True, null=True, verbose_name="sincronizado el")),
                ("client_uuid", models.UUIDField(blank=True, help_text="Idempotencia para registros offline.", null=True, verbose_name="UUID del cliente")),
                ("source_ip", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP de origen")),
                ("device_info", models.CharField(blank=True, max_length=200, verbose_name="dispositivo")),
                ("access_point", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="access_logs", to="core.accesspoint", verbose_name="punto de control")),
                ("badge", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="access_logs", to="solapines.badge", verbose_name="solapín")),
                ("registered_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="registrado por")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="access_logs", to=settings.AUTH_USER_MODEL, verbose_name="usuario")),
            ],
            options={
                "verbose_name": "registro de acceso",
                "verbose_name_plural": "bitácora de accesos",
                "ordering": ("-occurred_at",),
            },
        ),
        migrations.AddIndex(
            model_name="accesslog",
            index=models.Index(fields=["-occurred_at"], name="idx_accesslog_occurred"),
        ),
        migrations.AddIndex(
            model_name="accesslog",
            index=models.Index(fields=["campus", "-occurred_at"], name="idx_accesslog_campus_time"),
        ),
        migrations.AddIndex(
            model_name="accesslog",
            index=models.Index(fields=["result"], name="idx_accesslog_result"),
        ),
        migrations.AddIndex(
            model_name="accesslog",
            index=models.Index(fields=["identity_card"], name="idx_accesslog_ci"),
        ),
        migrations.AddConstraint(
            model_name="accesslog",
            constraint=models.UniqueConstraint(condition=models.Q(("client_uuid__isnull", False)), fields=("client_uuid",), name="uniq_accesslog_client_uuid"),
        ),
    ]
