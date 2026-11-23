"""``python manage.py seed_data`` — datos iniciales del SIGACU en un solo comando.

Aplica migraciones (crea las tablas si aún no existen), sincroniza los roles
institucionales, y crea sedes, áreas, puntos de control, nomencladores, plantilla
de solapín, usuarios de demostración (uno por rol) y registros de muestra para
que el dashboard y los módulos tengan información al primer arranque.

Uso::

    python manage.py seed_data               # migra + crea solo lo que falta
    python manage.py seed_data --reset       # elimina y recrea los datos demo
    python manage.py seed_data --no-demo     # solo nomencladores y roles
    python manage.py seed_data --no-migrate  # omite las migraciones automáticas

Resultado de un arranque limpio (``docker compose up`` o tras ``dropdb``):

* Tablas creadas por ``migrate``.
* 15 roles institucionales (``RoleDefinition``) y 4 sedes.
* 8 usuarios demo (uno por rol operativo) — contraseña ``Sigacu2026*``.
* ~15 días de accesos, solapines, visitas, incidencias, vehículos y notificaciones.
"""

from __future__ import annotations

import argparse
import random
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.access_control.models import AccessLog
from apps.core.catalogs import (
    AccessPoint,
    CampusSite,
    CatalogEntry,
    NivelAcceso,
    OrganizationalUnit,
)
from apps.core.constants import AccessLevel, Campus, MovementType, Role, UserType
from apps.incidents.models import Incident
from apps.notifications.models import Notification
from apps.solapines.models import Badge, BadgeTemplate
from apps.usuarios.models import User
from apps.vehicles.models import AuthorizedVehicle, VehicleMovement
from apps.visitors.models import VisitRequest

DEMO_USERS = [
    {
        "username": "yusimi.perez",
        "nombres": "Yusimí",
        "apellidos": "Pérez Leyva",
        "ci": "85042312345",
        "role": Role.SUPERADMIN,
        "tipo_usuario": UserType.WORKER,
        "campus_sede": Campus.CENTRAL,
        "area": "Dirección de Tecnologías de la Información",
        "cargo": "Administrador de Sistemas",
        "nivel_acceso": AccessLevel.FREE,
        "is_staff": True,
        "is_superuser": True,
        "email": "yusimi.perez@uho.edu.cu",
    },
    {
        "username": "raul.ramirez",
        "nombres": "Raúl",
        "apellidos": "Ramírez Tamayo",
        "ci": "79051803321",
        "role": Role.ADMIN,
        "tipo_usuario": UserType.WORKER,
        "campus_sede": Campus.CENTRAL,
        "area": "Dirección de Tecnologías de la Información",
        "cargo": "Especialista en Gestión de Datos",
        "nivel_acceso": AccessLevel.LIMITED,
        "is_staff": True,
        "email": "raul.ramirez@uho.edu.cu",
    },
    {
        "username": "eddy.fonseca",
        "nombres": "Eddy Reinier",
        "apellidos": "Fonseca Ochoa",
        "ci": "73122701187",
        "role": Role.SECURITY_DIRECTOR,
        "tipo_usuario": UserType.WORKER,
        "campus_sede": Campus.CENTRAL,
        "area": "Seguridad y Protección",
        "cargo": "Director",
        "nivel_acceso": AccessLevel.FREE,
        "email": "eddy.fonseca@uho.edu.cu",
    },
    {
        "username": "maite.rodriguez",
        "nombres": "Maité",
        "apellidos": "Rodríguez Pupo",
        "ci": "91030411098",
        "role": Role.SECURITY_OFFICER,
        "tipo_usuario": UserType.WORKER,
        "campus_sede": Campus.CENTRAL,
        "area": "Seguridad y Protección",
        "cargo": "Inspector de Acceso",
        "nivel_acceso": AccessLevel.LIMITED,
        "email": "maite.rodriguez@uho.edu.cu",
    },
    {
        "username": "osmani.vargas",
        "nombres": "Osmani",
        "apellidos": "Vargas Leyva",
        "ci": "80091522456",
        "role": Role.VISIT_APPROVER,
        "tipo_usuario": UserType.WORKER,
        "campus_sede": Campus.CENTRAL,
        "area": "Seguridad y Protección",
        "cargo": "Especialista Principal",
        "nivel_acceso": AccessLevel.LIMITED,
        "email": "osmani.vargas@uho.edu.cu",
    },
    {
        "username": "lourdes.columbie",
        "nombres": "Lourdes",
        "apellidos": "Columbié Santiesteban",
        "ci": "76072910233",
        "role": Role.MANAGER,
        "tipo_usuario": UserType.MANAGER,
        "campus_sede": Campus.CENTRAL,
        "area": "Facultad de Informática y Ciencias Exactas",
        "cargo": "Decana",
        "nivel_acceso": AccessLevel.FREE,
        "email": "lourdes.columbie@uho.edu.cu",
    },
    {
        "username": "diosbel.tamayo",
        "nombres": "Diosbel",
        "apellidos": "Tamayo Guerra",
        "ci": "03051234567",
        "role": Role.STUDENT,
        "tipo_usuario": UserType.STUDENT,
        "campus_sede": Campus.CENTRAL,
        "area": "Facultad de Informática y Ciencias Exactas",
        "cargo": "Ingeniería Informática · 3er año",
        "nivel_acceso": AccessLevel.STUDENT,
        "email": "diosbel.tamayo@uho.edu.cu",
    },
    {
        "username": "maricel.borges",
        "nombres": "Maricel",
        "apellidos": "Borges Álvarez",
        "ci": "78021405567",
        "role": Role.PROFESSOR,
        "tipo_usuario": UserType.TEACHER,
        "campus_sede": Campus.CENTRAL,
        "area": "Facultad de Ingeniería",
        "cargo": "Profesora Titular",
        "nivel_acceso": AccessLevel.LIMITED,
        "email": "maricel.borges@uho.edu.cu",
    },
]

DEMO_PASSWORD = "Sigacu2026*"

CAMPUSES = [
    ("CENTRAL", "Sede Central – Pueblo Nuevo", "Avenida de los Libertadores Km 3½"),
    ("PIEDRA_BLANCA", "Sede Piedra Blanca", "Carretera a Gibara"),
    ("PEDAGOGICA", "Sede Pedagógica – Mártires de Humboldt", "Calle Frexes"),
    ("CULTURA_FISICA", "Sede de Cultura Física", "Reparto Pedro Díaz Coello"),
]

UNITS = [
    ("Facultad de Informática y Ciencias Exactas", "FICE"),
    ("Facultad de Ingeniería", "FI"),
    ("Facultad de Ciencias Económicas y Empresariales", "FCEE"),
    ("Rectoría", "REC"),
    ("Seguridad y Protección", "SP"),
    ("Dirección de Tecnologías de la Información", "DTI"),
]

CATALOGS = {
    CatalogEntry.Kind.VEHICLE_TYPE: [
        ("AUTOMOVIL", "Automóvil"),
        ("MOTOCICLETA", "Motocicleta"),
        ("OMNIBUS", "Ómnibus"),
        ("CAMION", "Camión"),
        ("BICICLETA", "Bicicleta"),
    ],
    CatalogEntry.Kind.INCIDENT_TYPE: [
        ("ACCESO_DENEGADO", "Acceso denegado"),
        ("DOCUMENTO_NO_COINCIDE", "Documento no coincide"),
        ("VEHICULO_NO_AUTORIZADO", "Vehículo no autorizado"),
        ("CONDUCTA_INADECUADA", "Conducta inadecuada"),
        ("OTRO", "Otro"),
    ],
    CatalogEntry.Kind.DENIAL_REASON: [
        ("SOLAPIN_CANCELADO", "Solapín cancelado"),
        ("SOLAPIN_VENCIDO", "Solapín vencido"),
        ("SIN_SOLAPIN", "Sin solapín"),
        ("NIVEL_NO_PERMITIDO", "Nivel de acceso no permitido"),
    ],
    CatalogEntry.Kind.ACCESS_LEVEL: [
        (AccessLevel.FREE.value, "Acceso libre"),
        (AccessLevel.LIMITED.value, "Acceso limitado"),
        (AccessLevel.RESTRICTED.value, "Acceso restringido"),
        (AccessLevel.STUDENT.value, "Estudiante"),
        (AccessLevel.VISITOR.value, "Visitante"),
    ],
}

NIVELES_ACCESO = [
    (
        NivelAcceso.Name.ACCESO_LIBRE,
        "Entrada y circulación sin restricciones por todas las áreas de la sede.",
    ),
    (
        NivelAcceso.Name.PERMANENTE,
        "Autorización indefinida para trabajadores y cuadros con plaza fija.",
    ),
    (
        NivelAcceso.Name.LIMITADO,
        "Acceso restringido a determinadas áreas o franjas horarias.",
    ),
    (
        NivelAcceso.Name.ESTUDIANTE,
        "Acceso a las áreas docentes y de servicios durante el curso.",
    ),
    (
        NivelAcceso.Name.VISITANTE,
        "Acceso temporal sujeto a una solicitud de visita aprobada.",
    ),
]

ANGOL = [
    "Carlos Manuel Estévez Ruiz",
    "Anabel Marrero Pérez",
    "Reinaldo Pupo Castillo",
    "Dalila Rodríguez Peña",
    "Yusneidis Ochoa Tamayo",
    "Frank Leyva Pupo",
    "Joel Infante Reyes",
    "María Elena Sánchez Cruz",
]


class Command(BaseCommand):
    help = "Genera nomencladores, usuarios demo y datos de ejemplo del SIGACU."

    def execute(self, *args, **options):
        """Aplica migraciones y luego siembra los datos.

        ``migrate`` se ejecuta **antes** de abrir la transacción del comando y
        **fuera** de ella: en PostgreSQL no se pueden anidar las sentencias DDL
        de las migraciones dentro de una transacción abierta aquí, y en una base
        vacía ``migrate`` debe poder confirmar por sí mismo. En las pruebas el
        runner pasa ``--no-migrate`` para no migrar dentro de su transacción.
        """
        if not options.get("no_migrate"):
            self._migrate()
        return super().execute(*args, **options)

    def create_parser(self, prog_name, subcommand, **kwargs):
        """Añade ``--no-migrate`` sin exponerlo en ``--help``.

        Lo usa ``settings.testing`` (comando de prueba paralelo) para no
        ejecutar migraciones dentro de una transacción de prueba.
        """
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.add_argument(
            "--no-migrate",
            action="store_true",
            help=argparse.SUPPRESS,
        )
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina los registros de demostración antes de recrearlos.",
        )
        parser.add_argument(
            "--no-demo",
            action="store_true",
            help="Solo crea nomencladores, plantilla de solapín y usuarios por rol.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options["reset"]
        with_demo = not options.get("no_demo")

        if reset:
            self.stdout.write(self.style.WARNING("Eliminando datos previos de demostración…"))
            from django.db import models as django_models

            AccessLog.objects.all().delete()
            VehicleMovement.objects.all().delete()
            Incident.objects.all().delete()
            VisitRequest.objects.all().delete()
            # ``Badge`` tiene borrado lógico y su FK a ``User`` es PROTECT: hay
            # que borrar físicamente los solapines (también los "eliminados")
            # antes que los usuarios demo.
            django_models.QuerySet.delete(Badge.all_objects.all())
            BadgeTemplate.objects.all().delete()
            AuthorizedVehicle.objects.all().delete()
            Notification.objects.all().delete()
            User.objects.filter(username__in=[u["username"] for u in DEMO_USERS]).delete()

        roles = self._sync_roles()
        campuses = self._seed_campuses()
        units = self._seed_units(campuses)
        points = self._seed_points(campuses)
        self._seed_catalogs()
        self._seed_access_levels()
        templates = self._seed_templates()
        users = self._seed_users(campuses, units)
        self._seed_badges(users, templates)
        self._seed_vehicles(campuses)

        if with_demo:
            self._seed_access_logs(users, campuses, points)
            self._seed_visits(users, campuses)
            self._seed_incidents(users, campuses, points)
            self._seed_notifications(users)

        self.stdout.write(self.style.SUCCESS("\nDatos iniciales creados correctamente."))
        self.stdout.write(
            f"  Roles institucionales: {roles[0]} creados / {roles[1]} actualizados\n"
            f"  Sedes: {len(campuses)}\n"
            f"  Usuarios demo: {len(users)} (contraseña: {DEMO_PASSWORD})\n"
            "  Ejemplo: yusimi.perez / Sigacu2026* (superadministrador)\n"
        )

    # ------------------------------------------------------------------ setup
    def _migrate(self):
        """Crea/actualiza las tablas antes de sembrar datos.

        Se ejecuta **fuera** de la transacción del comando (ver ``handle``):
        cada migración decide si abre la suya y en PostgreSQL el DDL anidado
        falla. En ``--no-migrate`` o en pruebas se omite.
        """
        self.stdout.write("Aplicando migraciones (creación de tablas)…")
        call_command("migrate", interactive=False, verbosity=0)

    def _sync_roles(self) -> tuple[int, int]:
        """Crea/actualiza los roles institucionales (``sync_roles``)."""
        from apps.usuarios.constants import RoleCode, role_definition
        from apps.usuarios.models import RoleDefinition

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
            if not RoleDefinition.objects.filter(code=code.value).exists():
                defaults["permissions"] = meta["permissions"]
                RoleDefinition.objects.create(code=code.value, **defaults)
                created_count += 1
            else:
                RoleDefinition.objects.filter(code=code.value).update(**defaults)
                updated_count += 1
        return created_count, updated_count

    # ------------------------------------------------------------------ seed
    def _seed_campuses(self) -> dict[str, CampusSite]:
        result = {}
        for code, name, address in CAMPUSES:
            obj, _ = CampusSite.objects.update_or_create(
                code=code,
                defaults={"name": name, "address": address, "municipality": "Holguín"},
            )
            result[code] = obj
        return result

    def _seed_units(self, campuses) -> dict[str, OrganizationalUnit]:
        result = {}
        central = campuses["CENTRAL"]
        for name, acronym in UNITS:
            obj, _ = OrganizationalUnit.objects.get_or_create(
                name=name, defaults={"acronym": acronym, "campus": central}
            )
            result[acronym] = obj
        return result

    def _seed_points(self, campuses) -> list[AccessPoint]:
        points = []
        definitions = [
            ("CENTRAL", "ENT-PPAL", "Entrada principal", False),
            ("CENTRAL", "VEH-CENTRAL", "Acceso vehicular", True),
            ("PIEDRA_BLANCA", "ENT-PB", "Entrada principal", False),
            ("PIEDRA_BLANCA", "VEH-PB", "Acceso vehicular", True),
            ("PEDAGOGICA", "ENT-PED", "Entrada principal", False),
            ("CULTURA_FISICA", "ENT-CF", "Entrada principal", False),
        ]
        for campus_code, code, name, vehicle in definitions:
            obj, _ = AccessPoint.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "campus": campuses[campus_code],
                    "is_vehicle_access": vehicle,
                },
            )
            points.append(obj)
        return points

    def _seed_catalogs(self):
        for kind, entries in CATALOGS.items():
            for order, (code, name) in enumerate(entries):
                CatalogEntry.objects.get_or_create(
                    kind=kind, code=code, defaults={"name": name, "sort_order": order}
                )

    def _seed_access_levels(self):
        """Crea los 5 niveles de acceso oficiales (RF-09.3)."""
        for order, (nombre, descripcion) in enumerate(NIVELES_ACCESO):
            NivelAcceso.objects.get_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion, "sort_order": order},
            )

    def _seed_templates(self) -> dict[str, BadgeTemplate]:
        result = {}
        defaults_zones = {
            "photo": {"x": 6, "y": 20, "w": 30, "h": 34},
            "name": {"x": 40, "y": 22, "w": 54, "h": 12},
            "identity_card": {"x": 40, "y": 36, "w": 54, "h": 8},
            "qr": {"x": 62, "y": 56, "w": 30, "h": 30},
            "access_level": {"x": 6, "y": 80, "w": 50, "h": 10},
        }
        for user_type in (
            UserType.STUDENT,
            UserType.TEACHER,
            UserType.WORKER,
            UserType.MANAGER,
            UserType.VISITOR,
        ):
            obj, _ = BadgeTemplate.objects.get_or_create(
                name=f"Plantilla {user_type.label}",
                user_type=user_type.value,
                defaults={
                    "is_default": True,
                    "zones": defaults_zones,
                    "primary_color": "#14305C",
                    "secondary_color": "#D9A441",
                },
            )
            result[user_type.value] = obj
        return result

    def _seed_users(self, campuses, units) -> dict[str, User]:
        users: dict[str, User] = {}
        for data in DEMO_USERS:
            data = data.copy()
            username = data.pop("username")
            user, created = User.objects.get_or_create(username=username, defaults=data)
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            else:
                for field, value in data.items():
                    setattr(user, field, value)
                user.save()
            users[username] = user
        return users

    def _seed_badges(self, users, templates):
        from apps.solapines.services import nivel_acceso_por_defecto, plantilla_para

        for user in users.values():
            # ``plantilla_para`` resuelve la plantilla por defecto del tipo de
            # usuario (RF-03.1); no se crea un solapín sin plantilla.
            template = templates.get(user.tipo_usuario) or plantilla_para(user.tipo_usuario)
            if template is None:
                self.stderr.write(
                    f"  Aviso: no hay plantilla de solapín para {user.tipo_usuario}; "
                    f"se omite el solapín de {user.username}."
                )
                continue
            # RF-03.7: el nivel del solapín se deriva del tipo de usuario.
            nivel = nivel_acceso_por_defecto(user.tipo_usuario)
            if not Badge.objects.filter(user=user).exists():
                Badge.objects.create(
                    user=user,
                    template=template,
                    access_level=nivel,
                    expires_at=timezone.now() + timedelta(days=730),
                    valid_from=timezone.localdate() - timedelta(days=60),
                    valid_until=timezone.localdate() + timedelta(days=670),
                )
            # Se mantiene coherente el nivel del perfil con el del solapín
            # (RF-03.6 / RF-03.7): ambos salen de la misma regla.
            if user.nivel_acceso != nivel:
                user.nivel_acceso = nivel
                user.save(update_fields=["nivel_acceso"])

    def _seed_vehicles(self, campuses):
        vehicles = [
            ("H123456", "Automóvil", "Rectoría", "Transporte de directivos", None),
            ("H789012", "Ómnibus", "Dpto. Transporte", "Traslado de estudiantes", None),
            ("M045210", "Motocicleta", "Facultad de Ingeniería", "Uso personal autorizado", 500),
            ("H991044", "Camión", "Dpto. Mantenimiento", "Transporte de materiales", 60),
        ]
        for plate, vtype, owner, reason, days in vehicles:
            AuthorizedVehicle.objects.get_or_create(
                plate=plate,
                defaults={
                    "vehicle_type": vtype,
                    "owner_name": owner,
                    "authorization_reason": reason,
                    "campus": Campus.CENTRAL,
                    "valid_until": timezone.localdate() + timedelta(days=days) if days else None,
                },
            )

    def _seed_access_logs(self, users, campuses, points):
        if AccessLog.objects.exists():
            return
        extra_people = [
            {
                "full_name": name,
                "identity_card": f"9{10000000 + index:08d}",
                "user_type": UserType.VISITOR,
                "access_level": AccessLevel.VISITOR,
            }
            for index, name in enumerate(ANGOL)
        ]
        rnd = random.Random(2026)
        now = timezone.localtime()
        for day in range(14, -1, -1):
            base_date = now - timedelta(days=day)
            total = rnd.randint(40, 90) if day > 0 else 55
            for _ in range(total):
                if rnd.random() < 0.2:
                    person = rnd.choice(extra_people)
                    user_obj = None
                else:
                    user_obj = rnd.choice(list(users.values()))
                    person = user_obj
                hour = rnd.choices(
                    [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                    weights=[8, 14, 12, 10, 8, 6, 7, 9, 10, 8, 5],
                )[0]
                occurred = base_date.replace(
                    hour=hour, minute=rnd.randint(0, 59), second=rnd.randint(0, 59)
                )
                denied = rnd.random() < 0.06
                AccessLog.objects.create(
                    user=user_obj,
                    full_name=(person["full_name"] if user_obj is None else person.nombre_completo),
                    identity_card=(
                        person["identity_card"] if user_obj is None else person.identity_card
                    ),
                    user_type=(person["user_type"] if user_obj is None else person.user_type),
                    access_level=(
                        person["access_level"] if user_obj is None else person.access_level
                    ),
                    campus=rnd.choice([c for c in campuses.keys()]),
                    access_point=rnd.choice(points),
                    movement=rnd.choice([MovementType.ENTRY, MovementType.EXIT]),
                    result=AccessLog.Result.DENIED if denied else AccessLog.Result.GRANTED,
                    denial_reason="SOLAPIN_CANCELADO" if denied else "",
                    channel=AccessLog.Channel.WEB if rnd.random() > 0.3 else AccessLog.Channel.PWA,
                    occurred_at=occurred,
                )

    def _seed_visits(self, users, campuses):
        if VisitRequest.objects.exists():
            return
        manager = users["lourdes.columbie"]
        approver = users["osmani.vargas"]
        samples = [
            (
                "Anabel Marrero Pérez",
                "77051144210",
                "Facultad de Informática y Ciencias Exactas",
                "Taller de innovación con estudiantes",
                0,
                VisitRequest.Status.PENDING,
            ),
            (
                "Reinaldo Pupo Castillo",
                "65091233087",
                "Sede de Cultura Física",
                "Asesoría metodológica a entrenadores",
                0,
                VisitRequest.Status.PENDING,
            ),
            (
                "Carlos Manuel Estévez Ruiz",
                "93041255014",
                "Facultad de Ingeniería",
                "Asesoría sobre proyecto de colaboración",
                3,
                VisitRequest.Status.APPROVED,
            ),
        ]
        today = timezone.localdate()
        for name, ci, area, reason, offset, status in samples:
            vr = VisitRequest.objects.create(
                requester=manager,
                visitor_name=name,
                visitor_identity_card=ci,
                reason=reason,
                area=area,
                campus=Campus.CENTRAL,
                valid_from=today + timedelta(days=offset),
                valid_until=today + timedelta(days=offset + 1),
                status=status,
            )
            if status == VisitRequest.Status.APPROVED:
                vr.approve(approver, "Cumple los requisitos de seguridad.")

    def _seed_incidents(self, users, campuses, points):
        if Incident.objects.exists():
            return
        samples = [
            (
                "Acceso denegado: solapín cancelado",
                "ACCESO_DENEGADO",
                Incident.Severity.HIGH,
                Incident.Status.FOLLOW_UP,
                "Joel Infante Reyes",
            ),
            (
                "Documento no coincide con la persona",
                "DOCUMENTO_NO_COINCIDE",
                Incident.Severity.MEDIUM,
                Incident.Status.OPEN,
                "María Elena Sánchez Cruz",
            ),
            (
                "Vehículo no autorizado en acceso vehicular",
                "VEHICULO_NO_AUTORIZADO",
                Incident.Severity.MEDIUM,
                Incident.Status.CLOSED,
                "",
            ),
        ]
        for title, itype, severity, status, person in samples:
            Incident.objects.create(
                title=title,
                description=f"Incidencia registrada en el punto de control: {title}.",
                incident_type=itype,
                severity=severity,
                status=status,
                campus=Campus.CENTRAL,
                access_point=points[0],
                person_name=person,
                reported_by=users["maite.rodriguez"],
            )

    def _seed_notifications(self, users):
        notifications = [
            (
                "Solicitud de visita pendiente",
                "Existe una nueva solicitud de visita por revisar.",
                Notification.Category.VISIT,
            ),
            (
                "Alerta de seguridad",
                "Se registró un acceso denegado por solapín cancelado.",
                Notification.Category.SECURITY,
            ),
            (
                "Bienvenido al SIGACU",
                "Su cuenta ha sido configurada correctamente.",
                Notification.Category.SYSTEM,
            ),
        ]
        for user in users.values():
            for title, message, category in notifications:
                Notification.objects.get_or_create(
                    user=user,
                    title=title,
                    defaults={"message": message, "category": category},
                )
