"""Migración inicial del módulo de incidencias."""

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("access_control", "0001_initial"),
        ("usuarios", "0001_initial"),
        ("core", "0001_initial"),
        ("vehicles", "0001_initial"),
        ("visitors", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Incident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("code", models.CharField(blank=True, max_length=20, unique=True, verbose_name="código")),
                ("title", models.CharField(max_length=200, verbose_name="título")),
                ("description", models.TextField(verbose_name="descripción")),
                ("incident_type", models.CharField(max_length=50, verbose_name="tipo")),
                ("severity", models.CharField(choices=[("BAJA", "Baja"), ("MEDIA", "Media"), ("ALTA", "Alta"), ("CRITICA", "Crítica")], default="MEDIA", max_length=10, verbose_name="gravedad")),
                ("status", models.CharField(choices=[("ABIERTA", "Abierta"), ("SEGUIMIENTO", "En seguimiento"), ("CERRADA", "Cerrada"), ("DESESTIMADA", "Desestimada")], default="ABIERTA", max_length=15, verbose_name="estado")),
                ("campus", models.CharField(choices=[("CENTRAL", "Sede Central – Pueblo Nuevo"), ("PIEDRA_BLANCA", "Sede Piedra Blanca"), ("PEDAGOGICA", "Sede Pedagógica – Mártires de Humboldt"), ("CULTURA_FISICA", "Sede de Cultura Física"), ("OTRA", "Otra sede / dependencia")], max_length=20, verbose_name="sede")),
                ("person_name", models.CharField(blank=True, max_length=200, verbose_name="persona involucrada")),
                ("person_identity_card", models.CharField(blank=True, max_length=11, verbose_name="CI de la persona")),
                ("photo", models.ImageField(blank=True, null=True, upload_to="incidents/", verbose_name="evidencia fotográfica")),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="ocurrida el")),
                ("closed_at", models.DateTimeField(blank=True, null=True, verbose_name="cerrada el")),
                ("resolution", models.TextField(blank=True, verbose_name="resolución / acciones")),
                ("access_log", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incidents", to="access_control.accesslog")),
                ("access_point", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incidents", to="core.accesspoint")),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_incidents", to=settings.AUTH_USER_MODEL, verbose_name="asignada a")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="creado por")),
                ("reported_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reported_incidents", to=settings.AUTH_USER_MODEL, verbose_name="reportada por")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="actualizado por")),
                ("vehicle_movement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incidents", to="vehicles.vehiclemovement")),
                ("visit_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incidents", to="visitors.visitrequest")),
            ],
            options={
                "verbose_name": "incidencia",
                "verbose_name_plural": "incidencias",
                "ordering": ("-occurred_at",),
            },
        ),
        migrations.AddIndex(
            model_name="incident",
            index=models.Index(fields=["status"], name="idx_incident_status"),
        ),
        migrations.AddIndex(
            model_name="incident",
            index=models.Index(fields=["-occurred_at"], name="idx_incident_occurred"),
        ),
        migrations.CreateModel(
            name="IncidentFollowUp",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("comment", models.TextField(verbose_name="comentario")),
                ("new_status", models.CharField(blank=True, choices=[("ABIERTA", "Abierta"), ("SEGUIMIENTO", "En seguimiento"), ("CERRADA", "Cerrada"), ("DESESTIMADA", "Desestimada")], max_length=15, verbose_name="nuevo estado")),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="follow_ups", to="incidents.incident", verbose_name="incidencia")),
            ],
            options={
                "verbose_name": "seguimiento de incidencia",
                "verbose_name_plural": "seguimientos de incidencias",
                "ordering": ("-created_at",),
            },
        ),
    ]
