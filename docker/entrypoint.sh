#!/usr/bin/env sh
# =====================================================================
# UHO SIGACU — Punto de entrada del contenedor backend
# ---------------------------------------------------------------------
# 1. Espera a que PostgreSQL esté disponible.
# 2. Aplica migraciones.
# 3. Carga datos iniciales (solo si SEED_DATA=true).
# 4. Recolecta archivos estáticos (solo en producción).
# 5. Cede el control al comando recibido (Gunicorn / Daphne / runserver).
# =====================================================================
set -e

echo "⏳ [entrypoint] Esperando a PostgreSQL en ${POSTGRES_HOST}:${POSTGRES_PORT}…"
until nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT}"; do
  sleep 1
done
echo "✅ [entrypoint] PostgreSQL disponible."

echo "🔧 [entrypoint] Aplicando migraciones…"
python manage.py migrate --noinput

if [ "${SEED_DATA:-false}" = "true" ]; then
  echo "🌱 [entrypoint] Cargando datos iniciales…"
  python manage.py seed_data || echo "⚠️  seed_data falló (probablemente ya existen datos)."
fi

if [ "${COLLECT_STATIC:-false}" = "true" ]; then
  echo "📦 [entrypoint] Recolectando archivos estáticos…"
  python manage.py collectstatic --noinput
fi

if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
  echo "👤 [entrypoint] Creando/actualizando superusuario…"
  export DJANGO_SUPERUSER_USERNAME DJANGO_SUPERUSER_PASSWORD DJANGO_SUPERUSER_EMAIL
  python - <<'PYEOF' || echo "⚠️  No se pudo crear el superusuario (¿migraciones pendientes?)."
import os

import django

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"].strip().lower()
user, created = User.objects.get_or_create(
    username=username,
    defaults={
        "first_name": "Admin",
        "last_name": "SIGACU",
        "email": os.environ.get("DJANGO_SUPERUSER_EMAIL", ""),
        "is_staff": True,
        "is_superuser": True,
        "role": "SA",
        "user_type": "TRABAJADOR",
        "access_level": "LIBRE",
    },
)
user.is_staff = True
user.is_superuser = True
user.set_password(os.environ["DJANGO_SUPERUSER_PASSWORD"])
user.save()
print("Superusuario listo:", user.username, "(creado)" if created else "(actualizado)")
PYEOF
fi

echo "🚀 [entrypoint] Iniciando: $*"
exec "$@"
