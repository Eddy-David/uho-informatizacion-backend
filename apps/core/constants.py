"""Códigos de rol y catálogos constantes a nivel de sistema.

Los valores son estables porque se persisten en la base de datos (campo
``User.role``) y se comparten con el frontend para renderizar el menú.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    """Roles funcionales del SIGACU (requisitos §1 y matriz de §7)."""

    SUPERADMIN = "SA", _("Superadministrador")
    ADMIN = "ADM", _("Administrador")
    SECURITY_DIRECTOR = "DSP", _("Director de Seguridad y Protección")
    SECURITY_OFFICER = "SEG", _("Personal de Seguridad (Punto de Control)")
    VISIT_APPROVER = "AV", _("Aprobador de Visitas")
    MANAGER = "CUADRO", _("Cuadro / Directivo")
    USER = "USUARIO", _("Trabajador / Profesor / Estudiante")

    # Roles de los módulos universitarios. Deben coincidir con
    # ``apps.usuarios.constants.RoleCode``: el RBAC resuelve los permisos allí.
    STUDENT = "EST", _("Estudiante")
    PROFESSOR = "PROF", _("Profesor")
    ACADEMIC_AFFAIRS = "SEC_ACAD", _("Secretaría Docente")
    HR_OFFICER = "RRHH", _("Especialista de Recursos Humanos")
    MAINTENANCE_CHIEF = "MANT", _("Jefe de Mantenimiento")
    RESEARCH_LEAD = "INV", _("Jefe de Proyecto de Investigación")
    ANALYST = "ANAL", _("Analista Institucional")
    DATA_ENGINEER = "DATOS", _("Especialista en Datos")


#: Roles con acceso completo al panel de administración.
ADMIN_ROLES = (Role.SUPERADMIN, Role.ADMIN)

#: Roles que pueden operar los puntos de control.
ACCESS_ROLES = (Role.SUPERADMIN, Role.ADMIN, Role.SECURITY_DIRECTOR, Role.SECURITY_OFFICER)

#: Roles autorizados a gestionar credenciales.
CREDENTIAL_ROLES = (Role.SUPERADMIN, Role.ADMIN, Role.SECURITY_DIRECTOR)


class UserType(models.TextChoices):
    """Tipología de usuarios del campus (usada por el solapín digital)."""

    STUDENT = "ESTUDIANTE", _("Estudiante")
    TEACHER = "PROFESOR", _("Profesor")
    WORKER = "TRABAJADOR", _("Trabajador")
    MANAGER = "CUADRO", _("Cuadro / Directivo")
    VISITOR = "VISITANTE", _("Visitante")


class AccessLevel(models.TextChoices):
    """Nivel de acceso impreso en el Solapín Digital (RF-03.7)."""

    FREE = "LIBRE", _("Acceso libre")
    PERMANENT = "PERMANENTE", _("Acceso permanente")
    LIMITED = "LIMITADO", _("Acceso limitado")
    RESTRICTED = "RESTRINGIDO", _("Acceso restringido")
    STUDENT = "ESTUDIANTE", _("Estudiante")
    VISITOR = "VISITANTE", _("Visitante")


#: Nivel de acceso asignado por defecto a cada tipo de usuario (RF-03.7).
NIVEL_POR_DEFECTO = {
    UserType.MANAGER: AccessLevel.FREE,
    UserType.TEACHER: AccessLevel.PERMANENT,
    UserType.WORKER: AccessLevel.LIMITED,
    UserType.STUDENT: AccessLevel.STUDENT,
    UserType.VISITOR: AccessLevel.VISITOR,
}


def nivel_acceso_por_defecto(tipo_usuario: str) -> str:
    """Devuelve el nivel de acceso que corresponde al tipo de usuario (RF-03.7)."""
    return NIVEL_POR_DEFECTO.get(tipo_usuario, AccessLevel.LIMITED)


class Campus(models.TextChoices):
    """Sedes de la Universidad de Holguín."""

    CENTRAL = "CENTRAL", _("Sede Central – Pueblo Nuevo")
    PIEDRA_BLANCA = "PIEDRA_BLANCA", _("Sede Piedra Blanca")
    PEDAGOGICA = "PEDAGOGICA", _("Sede Pedagógica – Mártires de Humboldt")
    CULTURA_FISICA = "CULTURA_FISICA", _("Sede de Cultura Física")
    OTHER = "OTRA", _("Otra sede / dependencia")


class RecordStatus(models.TextChoices):
    """Estado genérico de entidades con ciclo de vida."""

    ACTIVE = "ACTIVO", _("Activo")
    INACTIVE = "INACTIVO", _("Inactivo")
    CANCELLED = "CANCELADO", _("Cancelado")


class MovementType(models.TextChoices):
    """Sentido del movimiento en un punto de control."""

    ENTRY = "ENTRADA", _("Entrada")
    EXIT = "SALIDA", _("Salida")
