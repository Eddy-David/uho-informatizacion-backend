"""Migración inicial del solapín digital."""

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import apps.core.utils


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("usuarios", "0001_initial"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BadgeTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="eliminado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="eliminado el")),
                ("name", models.CharField(max_length=120, verbose_name="nombre")),
                ("user_type", models.CharField(choices=[("ESTUDIANTE", "Estudiante"), ("PROFESOR", "Profesor"), ("TRABAJADOR", "Trabajador"), ("CUADRO", "Cuadro / Directivo"), ("VISITANTE", "Visitante")], default="ESTUDIANTE", max_length=20, verbose_name="tipo de usuario")),
                ("campus", models.CharField(blank=True, choices=[("CENTRAL", "Sede Central – Pueblo Nuevo"), ("PIEDRA_BLANCA", "Sede Piedra Blanca"), ("PEDAGOGICA", "Sede Pedagógica – Mártires de Humboldt"), ("CULTURA_FISICA", "Sede de Cultura Física"), ("OTRA", "Otra sede / dependencia")], max_length=20, verbose_name="sede")),
                ("background_image", models.ImageField(blank=True, null=True, upload_to="badges/templates/", verbose_name="imagen base")),
                ("primary_color", models.CharField(default="#14305C", max_length=9, verbose_name="color primario")),
                ("secondary_color", models.CharField(default="#D9A441", max_length=9, verbose_name="color secundario")),
                ("zones", models.JSONField(blank=True, default=dict, verbose_name="zonas dinámicas")),
                ("is_default", models.BooleanField(default=False, verbose_name="plantilla por defecto")),
                ("status", models.CharField(choices=[("ACTIVO", "Activo"), ("INACTIVO", "Inactivo"), ("CANCELADO", "Cancelado")], default="ACTIVO", max_length=20, verbose_name="estado")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="creado por")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="actualizado por")),
            ],
            options={
                "verbose_name": "plantilla de solapín",
                "verbose_name_plural": "plantillas de solapín",
                "ordering": ("-is_default", "name"),
            },
        ),
        migrations.CreateModel(
            name="BadgePrintJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("campus", models.CharField(blank=True, choices=[("CENTRAL", "Sede Central – Pueblo Nuevo"), ("PIEDRA_BLANCA", "Sede Piedra Blanca"), ("PEDAGOGICA", "Sede Pedagógica – Mártires de Humboldt"), ("CULTURA_FISICA", "Sede de Cultura Física"), ("OTRA", "Otra sede / dependencia")], max_length=20, verbose_name="sede")),
                ("area", models.CharField(blank=True, max_length=150, verbose_name="área")),
                ("user_type", models.CharField(blank=True, choices=[("ESTUDIANTE", "Estudiante"), ("PROFESOR", "Profesor"), ("TRABAJADOR", "Trabajador"), ("CUADRO", "Cuadro / Directivo"), ("VISITANTE", "Visitante")], max_length=20, verbose_name="tipo de usuario")),
                ("total", models.PositiveIntegerField(default=0, verbose_name="total")),
                ("processed", models.PositiveIntegerField(default=0, verbose_name="procesados")),
                ("status", models.CharField(choices=[("PENDIENTE", "Pendiente"), ("PROCESANDO", "Procesando"), ("LISTO", "Listo"), ("ERROR", "Error")], default="PENDIENTE", max_length=20, verbose_name="estado")),
                ("file", models.FileField(blank=True, null=True, upload_to="badges/print/", verbose_name="archivo generado")),
                ("error_message", models.TextField(blank=True, verbose_name="mensaje de error")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="creado por")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="actualizado por")),
            ],
            options={
                "verbose_name": "lote de impresión",
                "verbose_name_plural": "lotes de impresión",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="Badge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="eliminado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="eliminado el")),
                ("badge_number", models.CharField(max_length=30, unique=True, verbose_name="número de solapín")),
                ("access_level", models.CharField(choices=[("LIBRE", "Acceso libre"), ("LIMITADO", "Acceso limitado"), ("RESTRINGIDO", "Acceso restringido"), ("ESTUDIANTE", "Estudiante"), ("VISITANTE", "Visitante")], default="LIMITADO", max_length=20, verbose_name="nivel de acceso")),
                ("status", models.CharField(choices=[("ACTIVO", "Activo"), ("SUSPENDIDO", "Suspendido"), ("CANCELADO", "Cancelado"), ("VENCIDO", "Vencido")], default="ACTIVO", max_length=20, verbose_name="estado")),
                ("qr_token", models.CharField(default=apps.core.utils.generate_qr_token, max_length=64, unique=True, verbose_name="token QR")),
                ("issued_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="expedido el")),
                ("expires_at", models.DateTimeField(blank=True, null=True, verbose_name="vence el")),
                ("valid_from", models.DateField(blank=True, null=True, verbose_name="válido desde")),
                ("valid_until", models.DateField(blank=True, null=True, verbose_name="válido hasta")),
                ("notes", models.TextField(blank=True, verbose_name="observaciones")),
                ("template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="badges", to="solapines.badgetemplate", verbose_name="plantilla")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="badges", to=settings.AUTH_USER_MODEL, verbose_name="usuario")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="creado por")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="actualizado por")),
            ],
            options={
                "verbose_name": "solapín",
                "verbose_name_plural": "solapines",
                "ordering": ("-issued_at",),
            },
        ),
        migrations.AddIndex(
            model_name="badge",
            index=models.Index(fields=["qr_token"], name="idx_badge_qr_token"),
        ),
        migrations.AddIndex(
            model_name="badge",
            index=models.Index(fields=["status"], name="idx_badge_status"),
        ),
        migrations.AddConstraint(
            model_name="badge",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "ACTIVO")), fields=("user",), name="uniq_active_badge_per_user"),
        ),
    ]
