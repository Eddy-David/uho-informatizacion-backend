"""Gestión estudiantil — RF-11.

Esqueleto expandible del módulo universitario. La estructura sigue el mismo
patrón que los módulos operativos (models → serializers → views → urls) e
incluye RBAC por permisos y auditoría automática.

Pasos para completar el módulo:
  1. Definir reglas de negocio en ``services.py``.
  2. Ampliar modelos y crear migraciones (``makemigrations``).
  3. Añadir validaciones en ``serializers.py``.
  4. Exponer el servicio en ``views.py`` y consumirlo desde el frontend.
"""
