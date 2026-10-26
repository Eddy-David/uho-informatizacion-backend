# Backend — UHO SIGACU

API REST construida con **Django 4.2 + Django REST Framework**, con
autenticación JWT/OAuth2, WebSockets (Channels), almacenamiento MinIO y
exportaciones PDF/Excel.

## Ejecución rápida

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

- API: <http://localhost:8000/api/v1/>
- Swagger: <http://localhost:8000/api/docs/>
- Admin: <http://localhost:8000/admin/>

## Comandos

| Comando | Descripción |
|---|---|
| `python manage.py seed_data` | Datos demo (sedes, usuarios, accesos, visitas) |
| `python manage.py seed_data --reset` | Borra y recrea los datos demo |
| `python manage.py createsuperuser` | Superusuario del admin |
| `pytest` | Pruebas (usa `config.settings.testing`) |
| `black . && isort . && flake8` | Formato y calidad |
| `daphne config.asgi:application` | Servidor ASGI (HTTP + WebSockets) |
| `gunicorn config.wsgi:application` | Servidor WSGI de producción |

## Configuración

- `config/settings/base.py` — ajustes comunes (lee el `.env` de la raíz).
- `config/settings/development.py` — DEBUG, CORS amplio, canales en memoria.
- `config/settings/testing.py` — SQLite en memoria, hasher rápido.
- `config/settings/production.py` — seguridad estricta, MinIO obligatorio.

Selección vía `DJANGO_SETTINGS_MODULE`. Las variables se documentan en
`../.env.example`.

## Apps

| App | Responsabilidad |
|---|---|
| `core` | Nomencladores, permisos, paginación, exportaciones |
| `accounts` | Usuarios, roles, JWT/OAuth2 |
| `credentials` | Solapín digital y plantillas |
| `access_control` | Verificación y bitácora de accesos |
| `visitors` | Solicitudes de visita |
| `vehicles` | Vehículos y movimientos |
| `incidents` | Incidencias |
| `notifications` | Notificaciones + WebSocket |
| `reports` | Indicadores y exportaciones |

Documentación ampliada en [`../docs/`](../docs).
