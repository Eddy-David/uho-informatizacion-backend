"""Migración inicial del módulo de vehículos."""

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
    ]

    operations = [
        migrations.CreateModel(
            name="AuthorizedVehicle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("plate", models.CharField(max_length=20, unique=True, verbose_name="placa")),
                ("vehicle_type", models.CharField(default="Automóvil", max_length=50, verbose_name="tipo de vehículo")),
                ("brand", models.CharField(blank=True, max_length=80, verbose_name="marca")),
                ("model", models.CharField(blank=True, max_length=80, verbose_name="modelo")),
                ("color", models.CharField(blank=True, max_length=40, verbose_name="color")),
                ("owner_name", models.CharField(max_length=150, verbose_name="propietario / área")),
                ("owner_identity_card", models.CharField(blank=True, max_length=11, verbose_name="CI del propietario")),
                ("campus", models.CharField(blank=True, choices=[("CENTRAL", "Sede Central – Pueblo Nuevo"), ("PIEDRA_BLANCA", "Sede Piedra Blanca"), ("PEDAGOGICA", "Sede Pedagógica – Mártires de Humboldt"), ("CULTURA_FISICA", "Sede de Cultura Física"), ("OTRA", "Otra sede / dependencia")], max_length=20, verbose_name="sede")),
                ("authorization_reason", models.CharField(max_length=200, verbose_name="motivo de autorización")),
                ("valid_from", models.DateField(default=django.utils.timezone.localdate, verbose_name="válido desde")),
                ("valid_until", models.DateField(blank=True, help_text="Vacío = indefinida", null=True, verbose_name="válido hasta")),
                ("is_active", models.BooleanField(default=True, verbose_name="activo")),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="aprobado por")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="creado por")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="actualizado por")),
            ],
            options={
                "verbose_name": "vehículo autorizado",
                "verbose_name_plural": "vehículos autorizados",
                "ordering": ("plate",),
            },
        ),
        migrations.AddConstraint(
            model_name="authorizedvehicle",
            constraint=models.UniqueConstraint(fields=("plate",), name="uniq_vehicle_plate"),
        ),
        migrations.AddIndex(
            model_name="authorizedvehicle",
            index=models.Index(fields=["plate"], name="idx_vehicle_plate"),
        ),
        migrations.CreateModel(
            name="VehicleMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("plate", models.CharField(max_length=20, verbose_name="placa")),
                ("vehicle_type", models.CharField(blank=True, max_length=50, verbose_name="tipo de vehículo")),
                ("driver_name", models.CharField(blank=True, max_length=150, verbose_name="conductor")),
                ("driver_identity_card", models.CharField(blank=True, max_length=11, verbose_name="CI del conductor")),
                ("campus", models.CharField(blank=True, choices=[("CENTRAL", "Sede Central – Pueblo Nuevo"), ("PIEDRA_BLANCA", "Sede Piedra Blanca"), ("PEDAGOGICA", "Sede Pedagógica – Mártires de Humboldt"), ("CULTURA_FISICA", "Sede de Cultura Física"), ("OTRA", "Otra sede / dependencia")], max_length=20, verbose_name="sede")),
                ("movement", models.CharField(choices=[("ENTRADA", "Entrada"), ("SALIDA", "Salida")], max_length=10, verbose_name="movimiento")),
                ("authorized", models.BooleanField(default=False, verbose_name="autorizado")),
                ("is_exception", models.BooleanField(default=False, verbose_name="entrada por excepción")),
                ("reason", models.CharField(blank=True, max_length=255, verbose_name="motivo / observaciones")),
                ("status_after", models.CharField(choices=[("DENTRO", "Dentro"), ("FUERA", "Fuera")], max_length=10, verbose_name="estado")),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="ocurrido el")),
                ("access_point", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="core.accesspoint")),
                ("registered_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movements", to="vehicles.authorizedvehicle", verbose_name="vehículo")),
            ],
            options={
                "verbose_name": "movimiento de vehículo",
                "verbose_name_plural": "movimientos de vehículos",
                "ordering": ("-occurred_at",),
            },
        ),
        migrations.AddIndex(
            model_name="vehiclemovement",
            index=models.Index(fields=["plate", "-occurred_at"], name="idx_vehicle_move_plate"),
        ),
        migrations.AddIndex(
            model_name="vehiclemovement",
            index=models.Index(fields=["campus", "-occurred_at"], name="idx_vehicle_move_campus"),
        ),
    ]
