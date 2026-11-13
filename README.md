# Backend — SIGACU · Universidad de Holguín

API REST del **SIGACU (Sistema de Gestión de Acceso al Campus Universitario)**.
Construida con **Django 4.2 + Django REST Framework**, con autenticación
JWT/OAuth2, WebSockets (Channels), auditoría inmutable, almacenamiento MinIO y
exportaciones PDF/Excel.

La fuente de verdad funcional es el **Documento de Requerimientos v1.0 (junio
2026)** — citado abajo como «requisitos» — junto con el mockup interactivo. Este
README explica cómo está implementado cada requisito, qué está verificado y qué
queda pendiente; no sustituye a ese documento.

- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) — capas, modelo de datos, seguridad, despliegue.
- [docs/API.md](../docs/API.md) — referencia de endpoints. Swagger: <http://localhost:8000/api/docs/>.
- [docs/RBAC.md](../docs/RBAC.md) — roles y permisos. Es la referencia única del modelo de autorización.
- [docs/ROADMAP_MODULOS.md](../docs/ROADMAP_MODULOS.md) — hoja de ruta de los módulos universitarios.

---

## 1. Ejecución rápida

Requisitos: **Python 3.12**, **PostgreSQL 12+** y, solo para los PDF,
**WeasyPrint con sus librerías nativas** (Pango/Cairo; en Ubuntu
`libpango-1.0-0 libpangoft2-1.0-0 libcairo2`). Sin ellas el endpoint de PDF
responde `503` con un mensaje explicativo en lugar de fallar en silencio.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.example ../.env         # ajuste credenciales (base de datos, secretos)
python manage.py migrate
python manage.py seed_data         # sedes, plantillas, usuarios y datos demo
python manage.py runserver         # ASGI (Daphne): HTTP + WebSockets
```

- API: <http://localhost:8000/api/v1/>
- Swagger / OpenAPI: <http://localhost:8000/api/docs/> · <http://localhost:8000/api/schema/>
- Admin de Django: <http://localhost:8000/admin/>

Usuarios demo de `seed_data` (contraseña **`Sigacu2026*`**), uno por rol:
`yusimi.perez` (SA), `raul.ramirez` (ADM), `eddy.fonseca` (DSP),
`maite.rodriguez` (SEG), `osmani.vargas` (AV), `lourdes.columbie` (CUADRO),
`diosbel.tamayo` / `maricel.borges` (usuarios generales).

> **El servidor de desarrollo requiere ASGI** (`runserver` ya arranca Daphne en
> este proyecto) para que funcionen los WebSockets de notificaciones. En
> producción: `daphne config.asgi:application` o `gunicorn` + ASGI worker.

## 2. Comandos

| Comando | Descripción |
|---|---|
| `python manage.py seed_data` | Datos demo: sedes, unidades, plantillas, usuarios por rol, solapines y accesos |
| `python manage.py seed_data --reset` | Borra y recrea los datos demo |
| `python manage.py sync_roles --force` | Restablece la matriz rol → permisos por defecto (RBAC) |
| `python manage.py generar_accesos_demo` | Genera bitácora de accesos de ejemplo para los reportes |
| `python manage.py purge_audit` | Purga auditoría más antigua que `AUDIT_RETENTION_DAYS` |
| `python manage.py createsuperuser` | Superusuario del admin de Django |
| `pytest` | Suite completa con `config.settings.testing` |
| `black . && isort . && flake8` | Formato y calidad (lo exige la tubería de CI) |
| `makemigrations --check --dry-run` | Verifica que las migraciones estén versionadas (etapa de CI) |

## 3. Configuración

La configuración se selecciona con `DJANGO_SETTINGS_MODULE`:

| Módulo | Uso |
|---|---|
| `config.settings.development` | DEBUG, CORS amplio, canales en memoria, AGA_AUTH en modo `mock` |
| `config.settings.testing` | Sin throttling, hasher rápido, `InMemoryStorage`; se usa con `pytest` |
| `config.settings.production` | Seguridad estricta (HSTS, cookies seguras), MinIO y Redis obligatorios, AGA_AUTH en modo `real` |

Todas las variables se documentan en [`../.env.example`](../.env.example). Las
más relevantes para los requisitos:

| Variable | Requisito | Uso |
|---|---|---|
| `AGA_AUTH_MODE` | RF-01.1, RF-11.1 | `mock` (desarrollo) o `real` (contrato §11.1) |
| `AGA_AUTH_BASE_URL`, `AGA_AUTH_TOKEN`, `AGA_AUTH_ORIGIN` | RF-09.5, RF-11.1 | Endpoint y encabezados `Authorization`/`Origin` de AGA_AUTH |
| `SIGENU_ENABLED`, `SIGENU_BASE_URL`, `SIGENU_TOKEN` | RF-11.2 (RF-09.5) | Registro primario de estudiantes |
| `ASSET_ENABLED`, `ASSET_BASE_URL`, `ASSET_TOKEN` | RF-11.3 (RF-09.5) | Registro primario de trabajadores |
| `AUDIT_ENABLED`, `AUDIT_RETENTION_DAYS` | RNF-07, RF-09.6 | Auditoría transversal y retención |
| `USE_REDIS_CHANNEL_LAYER` / `USE_IN_MEMORY_CHANNEL_LAYER` | RF-10, RNF-05 | WebSockets con uno o varios procesos |
| `INSTITUTION_NAME`, `APP_NAME`, `APP_VERSION` | RG-05, RNF-11 | Cabeceras y pie de los PDF |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_SSL_REDIRECT` | RNF-06, RG-07 | Cifrado y control de origen |

Con `AGA_AUTH_MODE=mock` **no se valida la contraseña** (solo que no esté
vacía) y se emite una advertencia en los logs; es exclusivo para desarrollo y
laboratorio. Producción exige `AGA_AUTH_MODE=real`.

## 4. Apps

Las apps del repo son estas (no existen `accounts`/`credentials`: la identidad
está en `usuarios` y el solapín en `solapines`):

| App | Responsabilidad | Requisitos |
|---|---|---|
| `core` | Nomencladores genéricos, sedes/unidades/puntos de control, permisos, paginación, exportaciones PDF/Excel, auditoría, middleware | RG-10, RG-11, RF-09.3, RF-09.6 |
| `auditoria` | Modelo y consulta del log de auditoría | RF-09.6, RNF-07 |
| `usuarios` | Identidad local, cliente AGA_AUTH, JWT/OAuth2, roles y permisos | RF-01, RF-09.1, RF-09.2 |
| `access_control` | Verificación de acceso (motor de reglas), registro, bitácora, sincronización offline | RF-04, RF-12 |
| `solapines` | Plantillas, zonas dinámicas, composición PNG del solapín, QR, niveles de acceso | RF-02.3, RF-03 |
| `visitors` | Solicitudes de visita y su flujo de aprobación | RF-05 |
| `vehicles` | Vehículos autorizados, verificación de placa, movimientos | RF-06 |
| `incidents` | Incidencias y seguimiento | RF-07 |
| `notifications` | Notificaciones internas + WebSocket | RF-10 |
| `reports` | Dashboard, reportes tabulares y exportación PDF/Excel | RF-08, RF-12.4 |
| `students`, `academic`, `hr`, `maintenance`, `research`, `analytics` | Módulos universitarios (esqueleto funcional, sin UI) | Ver [roadmap](../docs/ROADMAP_MODULOS.md) |

## 5. Estado frente al Documento de Requerimientos

Leyenda: ✅ implementado y verificado · 🟡 parcial / depende de un sistema
externo o de configuración · ⬜ pendiente. «Verificado» significa que existe una
prueba automatizada (o una comprobación por HTTP durante la revisión) que lo
ejercita; se indica cuándo no la hay.

### 5.1 Institucionales (RG) y autenticación

| Código | Estado | Dónde / notas |
|---|---|---|
| RG-01 UX | ✅ | Interfaz en español, mensajes unificados; ver el README del frontend |
| RG-02/RG-09 Ciberseguridad | 🟡 | RBAC en todos los endpoints, JWT + revocación, límite de intentos y bloqueo de cuenta, cabeceras de seguridad, `SecurityHeadersMiddleware`; **HTTPS lo termina el proxy** y el refresh token vive en `localStorage` (ver frontend §6) |
| RG-03/RNF-10 Interoperabilidad | ✅ | REST + JSON, OpenAPI (`/api/schema/`), JWT y OAuth2 (`/oauth/`) |
| RG-04/RNF-08 Sostenibilidad | ✅ | Arquitectura por apps, servicios separados de las vistas, migraciones versionadas |
| RG-05/RNF-11 Identidad | 🟡 | Colores/logo configurables sin código (`INSTITUTION_NAME`, paleta); falta cargar los recursos oficiales del Manual UHO |
| RG-06 Autenticación centralizada | 🟡 | El cliente AGA_AUTH implementa el contrato completo (encabezados, 200/401/409/500); falta **probar contra el servicio real** en producción |
| RG-07/RNF-09 Responsive + PWA | ✅ | Frontend responsive; PWA instalable con precache y cola offline (frontend §9) |
| RG-10/RNF-07 Logs de auditoría | ✅ | `AuditEvent` inmutable con usuario, acción, módulo, fecha/hora, IP y correlación |
| RG-11 Nomencladores CRUD | ✅ | `CatalogEntry` (motor genérico) + vistas de sedes, unidades, puntos de control y niveles |
| RG-12 Roles y permisos | ✅ | Permisos atómicos `recurso:accion`, matriz editable en BD (`RoleDefinition`), `sync_roles` |

### 5.2 Funcionales (RF)

| Código | Estado | Implementación / notas |
|---|---|---|
| RF-01.1–01.3 Login AGA_AUTH | 🟡 | `AgaAuthClient` (`apps/usuarios/services.py`): modo `real` con el contrato §11.1 y creación/actualización del usuario local + emisión de JWT. Verificado en modo `mock` y con servidor simulado; falta la prueba de integración real |
| RF-01.2 Mensajes 200/401/409/500 | ✅ | Traducidos a mensajes en español en el cliente AGA y en la vista de login |
| RF-01.4 SA crea roles y asigna | ✅ | `RoleDefinition` + usuarios con `role`/`extra_permissions`; editable desde la API de administración |
| RF-01.5 Logout | ✅ | `POST /auth/logout/` revoca el refresh (blacklist) y notifica `/logout` a AGA_AUTH en modo `real` |
| RF-01.6 Expiración por inactividad | 🟡 | Lifetime del access token configurable (`SIMPLE_JWT`); no hay temporizador de inactividad en el cliente |
| RF-02.1–02.2 Perfil | ✅ | `GET /auth/me/` con datos personales y área/cargo o facultad/carrera |
| RF-02.3 Solapín propio | ✅ | `GET /solapines/mio/` y `GET /solapines/mio/imagen/` (PNG compuesto, descarga) |
| RF-02.4 Notificaciones | ✅ | `GET /notifications/` con `is_read` |
| RF-02.5 Datos no editables | ✅ | Solo se actualizan campos de administración (nivel de acceso, estado); los datos oficiales los escribe la sincronización |
| RF-03.1–03.3 Plantillas y composición | ✅ | Plantilla por tipo de usuario, zonas dinámicas (JSON) y composición con Pillow de foto, nombre, CI, tipo, nivel y QR |
| RF-03.4 Generación masiva | ✅ | `POST /solapines/badges/bulk-generate/` filtrando por sede/área/tipo |
| RF-03.5 Buscar por CI/nombre | ✅ | Búsqueda en el listado de solapines |
| RF-03.6 Cambio manual de nivel | ✅ | `POST /solapines/badges/{uuid}/access-level/`, auditado |
| RF-03.7 Niveles por defecto | ✅ | `NIVEL_POR_DEFECTO` en `core/constants.py` (Cuadro→LIBRE, Profesor→PERMANENTE, Trabajador→LIMITADO, Estudiante→ESTUDIANTE, Visitante→VISITANTE); cubierto por pruebas |
| RF-03.8 Solapín temporal de visitante | ✅ | Se genera al aprobar la solicitud, con vigencia de la visita |
| RF-03.9 QR sin datos personales | ✅ | El QR contiene solo el UUID del solapín; el estado se valida contra la BD; hay endpoint PNG |
| RF-03.10 Cancelar / reactivar | ✅ | Acciones `cancel` y `reactivate`, auditadas |
| RF-03.11 Configuración restringida | ✅ | Plantillas limitadas a SA/ADM/DSP |
| RF-04.1–04.2 QR o CI/nombre | ✅ | Motor de verificación por QR (UUID o JSON), CI y solapín |
| RF-04.3 Ficha | ✅ | Respuesta con datos de la persona, solapín, nivel y estado |
| RF-04.4/04.7 Permitido/denegado y alertas | ✅ | Resultado `allowed` con motivo; el frontend diferencia verde/rojo con motivo específico |
| RF-04.5 Registro de acceso | ✅ | Sede, fecha/hora, movimiento y usuario que registra; pruebas del motor y de los endpoints |
| RF-04.6 PWA | ✅ | Frontend (frontend §9); la verificación exige contexto seguro para la cámara |
| RF-04.8 Incidencia desde verificación | ✅ | Endpoint de incidencias accesible desde la pantalla (frontend) |
| RF-05.1–05.4 Flujo de visitas | ✅ | Crear (CUADRO), bandeja de pendientes (AV/DSP), aprobar / rechazar con motivo / solicitar cambios |
| RF-05.5 Editar y reenviar | ✅ | `PATCH /visitors/requests/{uuid}/estado/` devuelve a PENDIENTE |
| RF-05.6 Notificar al Cuadro | ✅ | Notificación interna en cada cambio de estado |
| RF-05.7 Solapín automático al aprobar | ✅ | Cubierto por pruebas («patch estado aprobada genera solapín») |
| RF-05.8 Historial de estados | ✅ | Historial de cambios persistido por solicitud |
| RF-06.1 Movimientos | ✅ | `POST /vehicles/register/` con placa, movimiento, sede, conductor y motivo |
| RF-06.2 Tipos de vehículo CRUD | ✅ | Nomenclador `TIPO_VEHICULO` vía `CatalogEntry` (RF-09.3) |
| RF-06.3 Catálogo autorizado | ✅ | CRUD `/vehicles/authorized/` con placa, tipo, propietario, motivo y vigencia |
| RF-06.4 Indicar si está autorizado | ✅ | `GET /vehicles/check/?plate=` |
| RF-06.5 Resaltar no autorizado | ✅ | El chequeo devuelve `authorized: false` y el frontend pinta alerta roja + entrada por excepción |
| RF-06.6 Asociar conductor | ✅ | `driver_name` / `driver_identity_card` en el movimiento |
| RF-06.7 Histórico con filtros | ✅ | `/vehicles/movements/` con filtros por sede, movimiento y placa, y `today=1` |
| RF-07.1 Registrar incidencia | ✅ | `POST /incidents/` con título, descripción, tipo, sede y quién reporta |
| RF-07.2 Tipos de incidencia CRUD | ✅ | Nomenclador `TIPO_INCIDENCIA` |
| RF-07.3 Estados | ✅ | Abierta / En seguimiento / Cerrada |
| RF-07.4 Referencias opcionales | ✅ | Asociación opcional a acceso, visita o movimiento vehicular |
| RF-07.5 Listar/filtrar | ✅ | Filtros por estado, gravedad, sede y tipo + búsqueda |
| RF-08.1–08.4 Reportes | ✅ | Reportes de accesos (por día, hora, sede, detalle y denegados), visitas, vehículos e incidencias con filtros de fecha/sede |
| RF-08.5 Dashboard | ✅ | `/reports/dashboard/`: accesos del día, visitas activas, vehículos dentro, incidencias abiertas y series por sede |
| RF-08.6 Exportar PDF/Excel | ✅ | `/reports/export/pdf/` y `/reports/export/excel/` para lista de accesos, visitas y vehículos; el PDF y el Excel se generan desde **los mismos datos** que la pantalla |
| RF-09.1 Gestión de usuarios | ✅ | CRUD, estadísticas, activación y restablecimiento de contraseña |
| RF-09.2 Roles y permisos granulares | ✅ | Ver [RBAC](../docs/RBAC.md); la matriz se edita sin desplegar código |
| RF-09.3 Nomencladores | 🟡 | Motor genérico `CatalogEntry` + sedes, áreas, puntos de control y niveles. Catálogos existentes: tipos de vehículo, tipos de incidencia, motivos de denegación, áreas de visita y genéricos. **Pendientes: cargos, carreras, tipos de curso y motivos de visita** (el motivo de visita se guarda como texto libre en la solicitud) |
| RF-09.4 Identidad visual | 🟡 | Parámetros configurables; falta el logo oficial |
| RF-09.5 Configurar integraciones | 🟡 | Las variables de AGA_AUTH/SIGENU/ASSET existen y se cargan; **no hay pantalla** que las edite en tiempo de ejecución |
| RF-09.6 Vista de logs de auditoría | ✅ | `/audit/events/` con filtros por acción, gravedad, módulo y actor, más `/audit/permissions/` |
| RF-10.1 Notificaciones internas | ✅ | Servicio `notify`/`notify_security_team` en eventos de visitas, solapines, accesos e incidencias |
| RF-10.2 Marcar leídas | ✅ | `/notifications/mark-read/` (por UUID o `all`) y `unread_count` |
| RF-10.3 Correo para eventos críticos | 🟡 | `EMAIL_BACKEND` configurable, pero no hay plantillas ni disparadores de correo definidos |
| RF-11.1 AGA_AUTH | 🟡 | Como RF-01.1 |
| RF-11.2 SIGENU | ⬜ | Solo existe la configuración (`SIGENU_*`); falta el cliente de consulta |
| RF-11.3 ASSET | ⬜ | Igual que SIGENU |
| RF-11.4 API propia documentada | ✅ | OpenAPI/Swagger/ReDoc con esquema versionado |
| RF-11.5 Token + auditoría de API | ✅ | JWT/OAuth2 en todos los recursos y `RequestAuditMiddleware` |
| RF-12.1 Sede en cada evento | ✅ | Accesos, vehículos, incidencias y solapines registran la sede |
| RF-12.2 Registros únicos | ✅ | Un registro primario por persona/solapín; la sede se asocia al evento |
| RF-12.3 Puntos de control por sede | ✅ | `core.AccessPoint` con sede, acceso vehicular y estado |
| RF-12.4 Reportes comparativos | ✅ | Reporte «Accesos por sede» y filtro por sede en dashboard y exportaciones |

### 5.3 No funcionales (RNF)

| Código | Estado | Notas |
|---|---|---|
| RNF-01 Usabilidad | ✅ | Mensajes en español; errores normalizados como `{error:{code,message,details}}` |
| RNF-02 Accesibilidad | 🟡 | Se aplica en la interfaz; no hay auditoría WCAG formal |
| RNF-03 Rendimiento (<2 s verificación, <3 s solapín) | 🟡 | Índices en bitácora y solapines y composición en memoria; no hay medición automatizada de latencia |
| RNF-04 Disponibilidad | 🟡 | Degradación controlada en el cliente (caché de perfil y cola offline); no hay modo de solo lectura en el servidor |
| RNF-05 Escalabilidad | ✅ | Sin estado en la app; Redis/PostgreSQL; operación multi-sede |
| RNF-06 Seguridad | 🟡 | Ver RG-02; falta certificado y cabeceras de proxy en el despliegue |
| RNF-07 Auditoría inmutable | ✅ | Sin edición desde la interfaz; purga solo por política de retención |
| RNF-12 Protección de datos | 🟡 | Minimización en respuestas y acceso por rol; el QR no expone datos personales; cifrado en reposo lo aporta la infraestructura |
| RNF-13 Reutilización | ✅ | Un motor de nomencladores y un solo módulo de exportación para todo el sistema |

## 6. Verificación

```bash
pytest                     # suite completa (config.settings.testing)
pytest apps/reports -v     # reportes y exportaciones PDF/Excel
flake8 . && black --check .   # calidad exigida por la tubería
```

En la última revisión: **84 pruebas pasan** (`84 passed`), sin fallos ni
omisiones, incluidas las de PDF (firma `%PDF`) y Excel (firma `PK`).

Dónde están las pruebas (y dónde no):

| Área | Archivo | Pruebas |
|---|---|---|
| Accesos: motor de reglas RF-04 | `apps/access_control/tests/test_services.py` y `test_rf04.py` | 24 |
| Solapines: composición, QR, niveles | `apps/solapines/tests.py` | 12 |
| Visitas: flujo completo de estados | `apps/visitors/tests.py` | 7 |
| Reportes y exportaciones | `apps/reports/tests.py` | 10 |
| Autenticación (JWT y AGA mock) | `apps/usuarios/tests/` | 11 |
| Auditoría | `apps/auditoria/tests.py` | 8 |
| Core (salud y API protegida) | `apps/core/tests/` | 2 |
| Módulos universitarios | `apps/*/tests/` | 1 cada uno (solo autenticación) |

**Sin pruebas automatizadas propias:** `vehicles`, `incidents` y
`notifications`. Sus flujos se ejercitaron por HTTP durante la revisión
(crear vehículo autorizado → verificación de placa → registro de entrada →
listado; incidencia → cambio de estado → estadísticas; notificaciones →
contador → marcar leídas) y funcionan, pero **deben añadirse pruebas** antes
de dar por cerrado el módulo. Igual ocurre con la exportación de la bitácora
(`/access/logs/export/…`), que no tiene test propio.

## 7. Pendientes conocidos

1. SIGENU y ASSET (RF-11.2/11.3): sin cliente. Es el bloqueo para que el perfil
   muestre facultad/carrera o área/cargo reales.
2. Prueba de integración real con AGA_AUTH y pantalla de configuración de
   integraciones (RF-09.5).
3. Catálogos de cargos, carreras y tipos de curso (RF-09.3).
4. Pruebas de vehículos, incidencias, notificaciones y exportación de bitácora.
5. Correos para eventos críticos (RF-10.3) y expiración por inactividad (RF-01.6).
6. Importación masiva desde SIGENU y reportes académicos del
   [roadmap](../docs/ROADMAP_MODULOS.md).

## 8. Solución de problemas

| Síntoma | Causa habitual | Solución |
|---|---|---|
| Los PDF responden `503` | WeasyPrint sin Pango/Cairo | Instale las librerías nativas (`docs/INSTALL_WINDOWS.md`, `docs/INSTALL_UBUNTU.md`) |
| Login acepta cualquier contraseña | `AGA_AUTH_MODE=mock` | Es lo esperado en desarrollo; producción usa `real` |
| WebSocket en `disconnected` | Servidor WSGI o sin Redis con varios procesos | Use Daphne/ASGI y `USE_REDIS_CHANNEL_LAYER=True` |
| `403` en un módulo | El rol no tiene el permiso | Revise la matriz en [RBAC.md](../docs/RBAC.md) o edite `RoleDefinition` |
| `makemigrations --check` falla en CI | Modelo cambiado sin migración | `python manage.py makemigrations` y versione el archivo |
