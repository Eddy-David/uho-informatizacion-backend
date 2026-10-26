"""Nomencladores básicos (RF-09.3) bajo nombres de dominio en español.

Los modelos viven en :mod:`apps.core.catalogs` junto al resto de nomencladores;
aquí sólo se exponen sus alias de dominio para que el resto del código pueda
importar ``Sede``, ``Area`` y ``NivelAcceso`` sin conocer el nombre técnico.

* ``Sede`` → :class:`apps.core.catalogs.CampusSite`
* ``Area`` → :class:`apps.core.catalogs.OrganizationalUnit`
* ``NivelAcceso`` → :class:`apps.core.catalogs.NivelAcceso`
"""

from apps.core.catalogs import CampusSite as Sede
from apps.core.catalogs import NivelAcceso
from apps.core.catalogs import OrganizationalUnit as Area

__all__ = ["Area", "NivelAcceso", "Sede"]
