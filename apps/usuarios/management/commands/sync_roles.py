"""``python manage.py sync_roles`` — sincroniza la matriz de roles con la BD.

Crea los roles definidos en ``apps.usuarios.constants`` y actualiza sus
metadatos. Los permisos **solo se sobrescriben** con ``--force`` para no
perder ajustes realizados desde la interfaz de administración.

Uso::

    python manage.py sync_roles            # crea los ausentes y actualiza metadatos
    python manage.py sync_roles --force    # además restablece los permisos por defecto
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.usuarios.constants import RoleCode, role_definition
from apps.usuarios.models import RoleDefinition


class Command(BaseCommand):
    help = "Crea/actualiza los roles institucionales y su matriz de permisos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Restablece los permisos de cada rol a los valores por defecto del código.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        force = options["force"]
        created_count = updated_count = 0

        for index, code in enumerate(RoleCode):
            meta = role_definition(code.value)
            defaults = {
                "label": meta["label"],
                "description": meta["description"],
                "module": meta["module"],
                "is_system": True,
                "sort_order": index,
            }
            if force or not RoleDefinition.objects.filter(code=code.value).exists():
                defaults["permissions"] = meta["permissions"]

            role, created = RoleDefinition.objects.update_or_create(
                code=code.value, defaults=defaults
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  + rol creado: {role.label}"))
            else:
                updated_count += 1
                self.stdout.write(
                    f"  ~ rol actualizado: {role.label} ({len(role.permissions)} permisos)"
                )

        from apps.usuarios.rbac import invalidate_role_cache

        invalidate_role_cache()
        self.stdout.write(
            self.style.SUCCESS(
                f"\nRoles sincronizados: {created_count} creados, {updated_count} actualizados."
            )
        )
        if force:
            self.stdout.write(
                self.style.WARNING("Los permisos fueron restablecidos a los valores por defecto.")
            )
