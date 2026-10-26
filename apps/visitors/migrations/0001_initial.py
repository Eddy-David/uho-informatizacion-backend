"""Migración inicial del módulo de visitantes."""

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
            name="VisitRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("code", models.CharField(blank=True, max_length=20, unique=True, verbose_name="código")),
                ("visitor_name", models.CharField(max_length=200, verbose_name="nombre del visitante")),
                ("visitor_identity_card", models.CharField(db_index=True, max_length=11, verbose_name="CI del visitante")),
                ("visitor_phone", models.CharField(blank=True, max_length=30, verbose_name="teléfono")),
                ("visitor_organization", models.CharField(blank=True, max_length=150, verbose_name="organización")),
                ("reason", models.TextField(verbose_name="motivo de la visita")),
                ("area", models.CharField(max_length=150, verbose_name="área a visitar")),
                ("campus", models.CharField(choices=[("CENTRAL", "Sede Central – Pueblo Nuevo"), ("PIEDRA_BLANCA", "Sede Piedra Blanca"), ("PEDAGOGICA", "Sede Pedagógica – Mártires de Humboldt"), ("CULTURA_FISICA", "Sede de Cultura Física"), ("OTRA", "Otra sede / dependencia")], max_length=20, verbose_name="sede")),
                ("valid_from", models.DateField(verbose_name="válida desde")),
                ("valid_until", models.DateField(verbose_name="válida hasta")),
                ("vehicle_plate", models.CharField(blank=True, max_length=20, verbose_name="placa del vehículo")),
                ("status", models.CharField(choices=[("PENDIENTE", "Pendiente"), ("APROBADA", "Aprobada"), ("RECHAZADA", "Rechazada"), ("CAMBIOS", "Cambios solicitados"), ("CANCELADA", "Cancelada"), ("FINALIZADA", "Finalizada")], default="PENDIENTE", max_length=20, verbose_name="estado")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="revisada el")),
                ("review_comment", models.TextField(blank=True, verbose_name="comentario de revisión")),
                ("attachments", models.FileField(blank=True, null=True, upload_to="visits/", verbose_name="documento adjunto")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="creado por")),
                ("requester", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="visit_requests", to=settings.AUTH_USER_MODEL, verbose_name="solicitante")),
                ("reviewer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_visits", to=settings.AUTH_USER_MODEL, verbose_name="aprobador")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="actualizado por")),
            ],
            options={
                "verbose_name": "solicitud de visita",
                "verbose_name_plural": "solicitudes de visita",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="visitrequest",
            index=models.Index(fields=["status"], name="idx_visit_request_status"),
        ),
        migrations.AddIndex(
            model_name="visitrequest",
            index=models.Index(fields=["-created_at"], name="idx_visit_request_created"),
        ),
        migrations.CreateModel(
            name="Visitor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("full_name", models.CharField(max_length=200, verbose_name="nombre completo")),
                ("identity_card", models.CharField(db_index=True, max_length=11, verbose_name="CI")),
                ("phone", models.CharField(blank=True, max_length=30, verbose_name="teléfono")),
                ("organization", models.CharField(blank=True, max_length=150, verbose_name="organización")),
                ("campus", models.CharField(choices=[("CENTRAL", "Sede Central – Pueblo Nuevo"), ("PIEDRA_BLANCA", "Sede Piedra Blanca"), ("PEDAGOGICA", "Sede Pedagógica – Mártires de Humboldt"), ("CULTURA_FISICA", "Sede de Cultura Física"), ("OTRA", "Otra sede / dependencia")], max_length=20, verbose_name="sede")),
                ("area", models.CharField(max_length=150, verbose_name="área")),
                ("valid_from", models.DateField(verbose_name="válido desde")),
                ("valid_until", models.DateField(verbose_name="válido hasta")),
                ("checked_in_at", models.DateTimeField(blank=True, null=True, verbose_name="entrada")),
                ("checked_out_at", models.DateTimeField(blank=True, null=True, verbose_name="salida")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="creado por")),
                ("host_user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="hosted_visitors", to=settings.AUTH_USER_MODEL, verbose_name="anfitrión")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="actualizado por")),
                ("user", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="visitor_profile", to=settings.AUTH_USER_MODEL, verbose_name="usuario temporal")),
                ("visit_request", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="visitor", to="visitors.visitrequest", verbose_name="solicitud")),
            ],
            options={
                "verbose_name": "visitante",
                "verbose_name_plural": "visitantes",
                "ordering": ("-created_at",),
            },
        ),
    ]
