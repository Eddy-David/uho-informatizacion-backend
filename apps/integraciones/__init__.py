"""Integraciones con los sistemas institucionales de la UHO.

Este paquete agrupa los adaptadores que conectan el SIGACU con los servicios
de la universidad. Los módulos de aquí **no** son aplicaciones Django: son
librerías que cualquier app de negocio puede importar cuando se activen las
credenciales reales (RNF-11: cambiar la integración sin tocar el dominio).

Subpaquetes:

* ``kit_uho`` — *uho-auth-kit* institucional (módulo ``uho_auth`` del kit,
  autenticación contra ``auth.uho.edu.cu`` / AGA_AUTH), Django REST Framework
  y documentación de la integración frontend (Vue/Pinia) del kit.
"""
