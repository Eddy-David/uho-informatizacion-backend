"""Migración inicial de la aplicación core (nomencladores compartidos)."""

import uuid

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CampusSite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="eliminado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="eliminado el")),
                ("code", models.CharField(max_length=30, unique=True, verbose_name="código")),
                ("name", models.CharField(max_length=120, verbose_name="nombre")),
                ("address", models.CharField(blank=True, max_length=200, verbose_name="dirección")),
                ("municipality", models.CharField(default="Holguín", max_length=80, verbose_name="municipio")),
                ("province", models.CharField(default="Holguín", max_length=80, verbose_name="provincia")),
                ("phone", models.CharField(blank=True, max_length=30, verbose_name="teléfono")),
                ("status", models.CharField(choices=[("ACTIVO", "Activo"), ("INACTIVO", "Inactivo"), ("CANCELADO", "Cancelado")], default="ACTIVO", max_length=20, verbose_name="estado")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="usuarios.user", verbose_name="creado por")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="usuarios.user", verbose_name="actualizado por")),
            ],
            options={
                "verbose_name": "sede",
                "verbose_name_plural": "sedes",
                "ordering": ("name",),
            },
        ),
        migrations.AddConstraint(
            model_name="campussite",
            constraint=models.UniqueConstraint(fields=("code",), name="uniq_campus_code"),
        ),
        migrations.CreateModel(
            name="OrganizationalUnit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="eliminado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="eliminado el")),
                ("name", models.CharField(max_length=150, verbose_name="nombre")),
                ("acronym", models.CharField(blank=True, max_length=30, verbose_name="siglas")),
                ("status", models.CharField(choices=[("ACTIVO", "Activo"), ("INACTIVO", "Inactivo"), ("CANCELADO", "Cancelado")], default="ACTIVO", max_length=20, verbose_name="estado")),
                ("campus", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="units", to="core.campussite", verbose_name="sede")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="usuarios.user", verbose_name="creado por")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="usuarios.user", verbose_name="actualizado por")),
            ],
            options={
                "verbose_name": "área organizativa",
                "verbose_name_plural": "áreas organizativas",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="AccessPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="eliminado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="eliminado el")),
                ("code", models.CharField(max_length=30, unique=True, verbose_name="código")),
                ("name", models.CharField(max_length=120, verbose_name="nombre")),
                ("is_vehicle_access", models.BooleanField(default=False, verbose_name="acceso vehicular")),
                ("status", models.CharField(choices=[("ACTIVO", "Activo"), ("INACTIVO", "Inactivo"), ("CANCELADO", "Cancelado")], default="ACTIVO", max_length=20, verbose_name="estado")),
                ("campus", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.campussite", verbose_name="sede")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="usuarios.user", verbose_name="creado por")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="usuarios.user", verbose_name="actualizado por")),
            ],
            options={
                "verbose_name": "punto de control",
                "verbose_name_plural": "puntos de control",
                "ordering": ("campus", "name"),
            },
        ),
        migrations.AddConstraint(
            model_name="accesspoint",
            constraint=models.UniqueConstraint(fields=("code",), name="uniq_access_point_code"),
        ),
        migrations.CreateModel(
            name="CatalogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="creado el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado el")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="eliminado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="eliminado el")),
                ("kind", models.CharField(choices=[("TIPO_VEHICULO", "Tipo de vehículo"), ("TIPO_INCIDENCIA", "Tipo de incidencia"), ("MOTIVO_DENEGACION", "Motivo de denegación"), ("AREA_VISITA", "Área de visita"), ("NIVEL_ACCESO", "Nivel de acceso"), ("GENERICO", "Genérico")], max_length=30, verbose_name="nomenclador")),
                ("code", models.CharField(max_length=50, verbose_name="código")),
                ("name", models.CharField(max_length=120, verbose_name="nombre")),
                ("description", models.TextField(blank=True, verbose_name="descripción")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="orden")),
                ("is_active", models.BooleanField(default=True, verbose_name="activo")),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="usuarios.user", verbose_name="creado por")),
                ("updated_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="usuarios.user", verbose_name="actualizado por")),
            ],
            options={
                "verbose_name": "entrada de nomenclador",
                "verbose_name_plural": "nomencladores",
                "ordering": ("kind", "sort_order", "name"),
            },
        ),
        migrations.AddConstraint(
            model_name="catalogentry",
            constraint=models.UniqueConstraint(fields=("kind", "code"), name="uniq_catalog_kind_code"),
        ),
    ]
