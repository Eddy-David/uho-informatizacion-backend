"""
Catálogo de permisos, roles y política de credenciales.

Este módulo es la **fuente única de verdad** del RBAC del SIGACU:

* ``Permission``  → permisos atómicos por recurso y acción (``recurso:accion``).
* ``RoleCode``    → roles institucionales (3 actuales + 7 preparados).
* ``ROLE_DEFINITIONS`` → matriz por defecto que se sincroniza a la base de datos.

Los permisos efectivos de un usuario se calculan en ``apps.usuarios.rbac`` y se
exponen en ``/auth/me/`` y en el token JWT (claim ``permissions``).
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Permisos atómicos — nombres estables (se guardan en la BD)
# ---------------------------------------------------------------------------
class Permission(models.TextChoices):
    """Nombre ``recurso:accion``. Las vistas usan ``HasPerm(Permission.X)``."""

    # --- Núcleo y administración ------------------------------------------
    DASHBOARD_VIEW = "dashboard:view", _("Ver el panel de inicio")
    PROFILE_VIEW = "profile:view", _("Ver el perfil propio")
    NOTIFICATIONS_VIEW = "notifications:view", _("Ver notificaciones")

    # --- Control de acceso ------------------------------------------------
    ACCESS_VERIFY = "access:verify", _("Verificar accesos en punto de control")
    ACCESS_VIEW = "access:view", _("Consultar la bitácora de accesos")
    ACCESS_EXPORT = "access:export", _("Exportar la bitácora")

    # --- Solapín digital --------------------------------------------------
    CREDENTIALS_VIEW = "credentials:view", _("Consultar solapines")
    CREDENTIALS_MANAGE = "credentials:manage", _("Gestionar solapines")
    CREDENTIALS_TEMPLATES = "credentials:templates", _("Configurar plantillas del solapín")

    # --- Visitantes -------------------------------------------------------
    VISITS_REQUEST = "visits:request", _("Solicitar visitas")
    VISITS_APPROVE = "visits:approve", _("Aprobar o rechazar visitas")
    VISITS_VIEW = "visits:view", _("Consultar visitantes")

    # --- Vehículos --------------------------------------------------------
    VEHICLES_VIEW = "vehicles:view", _("Consultar vehículos")
    VEHICLES_REGISTER = "vehicles:register", _("Registrar movimientos vehiculares")
    VEHICLES_MANAGE = "vehicles:manage", _("Administrar vehículos autorizados")

    # --- Incidencias ------------------------------------------------------
    INCIDENTS_VIEW = "incidents:view", _("Consultar incidencias")
    INCIDENTS_MANAGE = "incidents:manage", _("Registrar y cerrar incidencias")

    # --- Reportes ---------------------------------------------------------
    REPORTS_VIEW = "reports:view", _("Ver reportes y estadísticas")
    REPORTS_EXPORT = "reports:export", _("Exportar reportes (PDF/Excel)")

    # --- Administración ---------------------------------------------------
    USERS_VIEW = "users:view", _("Consultar usuarios")
    USERS_MANAGE = "users:manage", _("Gestionar usuarios")
    ROLES_MANAGE = "roles:manage", _("Gestionar roles y permisos")
    CATALOGS_VIEW = "catalogs:view", _("Consultar nomencladores")
    CATALOGS_MANAGE = "catalogs:manage", _("Gestionar nomencladores")
    CONFIG_MANAGE = "config:manage", _("Administrar configuración del sistema")

    # --- Auditoría --------------------------------------------------------
    AUDIT_VIEW = "audit:view", _("Consultar la auditoría")
    AUDIT_EXPORT = "audit:export", _("Exportar la auditoría")

    # --- Infermería / salud universitaria --------------------------------
    HEALTH_VIEW = "health:view", _("Consultar datos de salud del personal o estudiantes")

    # --- Módulos futuros: gestión estudiantil ----------------------------
    STUDENTS_VIEW = "students:view", _("Consultar estudiantes")
    STUDENTS_MANAGE = "students:manage", _("Gestionar estudiantes")

    # --- Módulos futuros: procesos académicos ----------------------------
    ACADEMIC_VIEW = "academic:view", _("Consultar procesos académicos")
    ACADEMIC_MANAGE = "academic:manage", _("Gestionar procesos académicos")

    # --- Módulos futuros: recursos humanos -------------------------------
    HR_VIEW = "hr:view", _("Consultar expedientes de personal")
    HR_MANAGE = "hr:manage", _("Gestionar recursos humanos")

    # --- Módulos futuros: mantenimiento ----------------------------------
    MAINTENANCE_VIEW = "maintenance:view", _("Consultar mantenimiento")
    MAINTENANCE_MANAGE = "maintenance:manage", _("Gestionar órdenes de mantenimiento")

    # --- Módulos futuros: proyectos de investigación ---------------------
    RESEARCH_VIEW = "research:view", _("Consultar proyectos de investigación")
    RESEARCH_MANAGE = "research:manage", _("Gestionar proyectos de investigación")

    # --- Módulos futuros: analítica --------------------------------------
    ANALYTICS_VIEW = "analytics:view", _("Ver analítica institucional")
    ANALYTICS_MANAGE = "analytics:manage", _("Configurar modelos y tableros analíticos")

    # --- Módulos de datos institucionales --------------------------------
    DATOS_VIEW = "datos:view", _("Consultar indicadores de datos institucionales")
    DATOS_MANAGE = "datos:manage", _("Administrar la ingesta y gobernanza del dato")


ALL_PERMISSIONS: frozenset[str] = frozenset(choice.value for choice in Permission)


# ---------------------------------------------------------------------------
# Roles institucionales
# ---------------------------------------------------------------------------
class RoleCode(models.TextChoices):
    # Roles operativos actuales
    SUPERADMIN = "SA", _("Superadministrador")
    ADMIN = "ADM", _("Administrador")
    SECURITY_DIRECTOR = "DSP", _("Director de Seguridad y Protección")
    SECURITY_OFFICER = "SEG", _("Personal de Seguridad (Punto de Control)")
    VISIT_APPROVER = "AV", _("Aprobador de Visitas")
    MANAGER = "CUADRO", _("Cuadro / Directivo")
    USER = "USUARIO", _("Trabajador / Profesor / Estudiante")

    # Roles preparados para los módulos futuros (RF-11 … RF-15)
    STUDENT = "EST", _("Estudiante")
    PROFESSOR = "PROF", _("Profesor")
    ACADEMIC_AFFAIRS = "SEC_ACAD", _("Secretaría Docente")
    HR_OFFICER = "RRHH", _("Especialista de Recursos Humanos")
    MAINTENANCE_CHIEF = "MANT", _("Jefe de Mantenimiento")
    RESEARCH_LEAD = "INV", _("Jefe de Proyecto de Investigación")
    ANALYST = "ANAL", _("Analista Institucional")
    DATA_ENGINEER = "DATOS", _("Especialista en Datos")


#: Roles que conservan acceso total al sistema.
FULL_ACCESS_ROLES = (RoleCode.SUPERADMIN,)

#: Alias heredados (compatibilidad con el código previo: ``Role``).
Role = RoleCode


_DEFAULT_BY_ROLE: dict[str, tuple[str, ...]] = {
    RoleCode.SUPERADMIN: ("*",),
    RoleCode.ADMIN: tuple(sorted(ALL_PERMISSIONS - {Permission.DATOS_MANAGE})),
    RoleCode.SECURITY_DIRECTOR: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.ACCESS_VERIFY,
        Permission.ACCESS_VIEW,
        Permission.ACCESS_EXPORT,
        Permission.CREDENTIALS_VIEW,
        Permission.CREDENTIALS_MANAGE,
        Permission.CREDENTIALS_TEMPLATES,
        Permission.VISITS_APPROVE,
        Permission.VISITS_VIEW,
        Permission.VEHICLES_VIEW,
        Permission.VEHICLES_REGISTER,
        Permission.VEHICLES_MANAGE,
        Permission.INCIDENTS_VIEW,
        Permission.INCIDENTS_MANAGE,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
        Permission.AUDIT_VIEW,
    ),
    RoleCode.SECURITY_OFFICER: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.ACCESS_VERIFY,
        Permission.ACCESS_VIEW,
        Permission.CREDENTIALS_VIEW,
        Permission.VEHICLES_VIEW,
        Permission.VEHICLES_REGISTER,
        Permission.INCIDENTS_VIEW,
        Permission.INCIDENTS_MANAGE,
    ),
    RoleCode.VISIT_APPROVER: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.VISITS_APPROVE,
        Permission.VISITS_VIEW,
    ),
    RoleCode.MANAGER: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.VISITS_REQUEST,
        Permission.VISITS_VIEW,
        Permission.REPORTS_VIEW,
        Permission.RESEARCH_VIEW,
    ),
    RoleCode.USER: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
    ),
    RoleCode.STUDENT: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.STUDENTS_VIEW,
        Permission.ACADEMIC_VIEW,
    ),
    RoleCode.PROFESSOR: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.STUDENTS_VIEW,
        Permission.ACADEMIC_VIEW,
        Permission.RESEARCH_VIEW,
        Permission.RESEARCH_MANAGE,
    ),
    RoleCode.ACADEMIC_AFFAIRS: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.STUDENTS_VIEW,
        Permission.STUDENTS_MANAGE,
        Permission.ACADEMIC_VIEW,
        Permission.ACADEMIC_MANAGE,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
    ),
    RoleCode.HR_OFFICER: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.HR_VIEW,
        Permission.HR_MANAGE,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
    ),
    RoleCode.MAINTENANCE_CHIEF: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.MAINTENANCE_VIEW,
        Permission.MAINTENANCE_MANAGE,
    ),
    RoleCode.RESEARCH_LEAD: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.RESEARCH_VIEW,
        Permission.RESEARCH_MANAGE,
        Permission.REPORTS_VIEW,
    ),
    RoleCode.ANALYST: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.ANALYTICS_VIEW,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
        Permission.ACADEMIC_VIEW,
        Permission.STUDENTS_VIEW,
        Permission.HR_VIEW,
        Permission.AUDIT_VIEW,
    ),
    RoleCode.DATA_ENGINEER: (
        Permission.DASHBOARD_VIEW,
        Permission.PROFILE_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_MANAGE,
        Permission.DATOS_VIEW,
        Permission.DATOS_MANAGE,
        Permission.AUDIT_VIEW,
    ),
}


#: Mapa completo ``rol → permisos por defecto`` (usado por la sincronización y la caché).
ROLE_DEFINITIONS = _DEFAULT_BY_ROLE


def default_permissions_for(role_code: str) -> list[str]:
    """Permisos por defecto de un rol (lista vacía si el código es desconocido)."""
    return list(_DEFAULT_BY_ROLE.get(role_code, ()))


def role_definition(role_code: str) -> dict:
    """Metadatos del rol: etiqueta, descripción, módulo funcional y permisos."""
    try:
        code = RoleCode(role_code)
    except ValueError:
        return {}
    label = str(code.label)
    return {
        "code": code.value,
        "label": label,
        "description": _ROLE_DESCRIPTIONS.get(code.value, ""),
        "module": _ROLE_MODULE.get(code.value, "core"),
        "future": _ROLE_MODULE.get(code.value, "core") != "core",
        "permissions": default_permissions_for(code.value),
    }


#: Módulo funcional al que pertenece cada rol (útil para agrupar en el frontend).
_ROLE_MODULE = {
    RoleCode.STUDENT: "students",
    RoleCode.PROFESSOR: "academic",
    RoleCode.ACADEMIC_AFFAIRS: "academic",
    RoleCode.HR_OFFICER: "hr",
    RoleCode.MAINTENANCE_CHIEF: "maintenance",
    RoleCode.RESEARCH_LEAD: "research",
    RoleCode.ANALYST: "analytics",
    RoleCode.DATA_ENGINEER: "analytics",
}

_ROLE_DESCRIPTIONS = {
    RoleCode.SUPERADMIN: "Acceso total, incluida la gestión de roles y la administración técnica.",
    RoleCode.ADMIN: "Administración funcional del sistema sin gestión de roles ni de datos.",
    RoleCode.SECURITY_DIRECTOR: "Gestión integral de la seguridad y protección del campus.",
    RoleCode.SECURITY_OFFICER: "Operación de puntos de control, vehículos e incidencias.",
    RoleCode.VISIT_APPROVER: "Revisión y decisión sobre solicitudes de visita.",
    RoleCode.MANAGER: "Solicitud de visitas y consulta de indicadores de su área.",
    RoleCode.USER: "Acceso básico: panel, perfil y notificaciones.",
    RoleCode.STUDENT: "Consulta de datos académicos propios y trámites estudiantiles.",
    RoleCode.PROFESSOR: "Gestión docente: estudiantes, evaluación e investigación.",
    RoleCode.ACADEMIC_AFFAIRS: "Matrícula, expedientes y control académico.",
    RoleCode.HR_OFFICER: "Expedientes laborales, plantillas y nómina.",
    RoleCode.MAINTENANCE_CHIEF: "Órdenes de trabajo, equipos e inventario técnico.",
    RoleCode.RESEARCH_LEAD: "Proyectos, publicaciones y financiamiento.",
    RoleCode.ANALYST: "Tableros institucionales y análisis de datos agregados.",
    RoleCode.DATA_ENGINEER: "Ingestión de datos y gobernanza del dato institucional.",
}

#: Descripciones de los permisos (para la pantalla de gestión de roles).
PERMISSION_LABELS: dict[str, str] = {choice.value: str(choice.label) for choice in Permission}


# ---------------------------------------------------------------------------
# Constantes de negocio (algunas importadas por el frontend vía la API)
# ---------------------------------------------------------------------------
#: Número máximo de intentos fallidos de autenticación antes de bloqueo temporal.
MAX_LOGIN_ATTEMPTS = 5

#: Minutos de bloqueo tras superar ``MAX_LOGIN_ATTEMPTS``.
LOGIN_LOCKOUT_MINUTES = 15

#: Duración mínima exigida a la contraseña (debe coincidir con settings).
MIN_PASSWORD_LENGTH = 8
