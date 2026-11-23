#!/usr/bin/env sh
# =====================================================================
# UHO SIGACU — Punto de entrada del contenedor backend
# ---------------------------------------------------------------------
# 1. Espera a que PostgreSQL esté disponible.
# 2. Aplica migraciones.
# 3. Carga datos iniciales solo en el PRIMER arranque (SEED_DATA=true y la base
#    de datos aún vacía); así ``docker compose restart`` conserva los datos.
# 4. Recolecta archivos estáticos (solo en producción).
# 5. Cede el control al comando recibido (Gunicorn / Daphne / runserver).
# =====================================================================
set -e

if [ -z "${DJANGO_SETTINGS_MODULE}" ]; then
  export DJANGO_SETTINGS_MODULE=config.settings.production
fi

echo "⏳ [entrypoint] Esperando a PostgreSQL en ${POSTGRES_HOST}:${POSTGRES_PORT}…"
until nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT}"; do
  sleep 1
done
echo "✅ [entrypoint] PostgreSQL disponible."

echo "🔧 [entrypoint] Aplicando migraciones…"
python manage.py migrate --noinput

if [ "${SEED_DATA:-false}" = "true" ]; then
  FIRST_BOOT=$(python - <<'PYEOF'
import django

django.setup()

from django.contrib.auth import get_user_model

print("1" if not get_user_model().objects.exists() else "0")
PYEOF
  )
  if [ "${FIRST_BOOT}" = "1" ]; then
    echo "🌱 [entrypoint] Primer arranque: cargando datos iniciales (seed_data)…"
    python manage.py seed_data
  else
    echo "⏭️  [entrypoint] La base de datos ya tiene usuarios: no se vuelve a sembrar."
  fi
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
