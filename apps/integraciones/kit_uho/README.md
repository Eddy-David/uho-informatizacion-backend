# uho-auth-kit (copia de integración)

Copia del **kit institucional `uho-auth-kit`** entregado a la UHO, integrada en
el backend del SIGACU en:

```
backend/apps/integraciones/kit_uho/
├── __init__.py          # uho_login + kit_disponible()
├── urls.py              # /api/v1/integraciones/kit/auth/  (solo si UHO_KIT_ENABLED=true)
└── uho_auth/
    ├── __init__.py
    ├── client.py        # POST auth.uho.edu.cu → perfil normalizado
    ├── views.py         # LoginView/LogoutView con Token DRF (opcionales)
    └── urls.py
```

## Qué es

Autenticación contra `auth.uho.edu.cu` (Django REST Framework + Vue 3/Pinia),
extraída del proyecto *human-resources* de la UHO. Flujo original:

> el frontend envía usuario/contraseña a `auth/login/` → el backend prueba
> primero un usuario local de Django y, si no existe, valida contra
> `auth.uho.edu.cu` → crea el usuario local si hace falta → devuelve un Token DRF.

## Diferencias con el kit original

| Aspecto | Kit original | Integración SIGACU |
|---|---|---|
| Origen de la configuración | `os.environ` leído al importar | `settings.UHO_INTEGRATIONS["AGA_AUTH"]` ← `.env` (RNF-11) |
| Variable del token | `UHO_API_KEY` | `AGA_AUTH_TOKEN` (alias `UHO_API_KEY` soportado) |
| URL | `UHO_AUTH_URL` con `/login` incluido | `AGA_AUTH_BASE_URL` (origen) → se añade `/login` |
| Rutas | `path("auth/", include(...))` en la raíz | `/api/v1/integraciones/kit/auth/`, solo si `UHO_KIT_ENABLED=true` |
| Formato de respuesta | `username, name, surname, national_id, user_type, active` | además `dni, nombres, apellidos, tipo_usuario, correo` (mismo dict que `AgaAuthClient`) |

Con esto, **el kit no añade dependencias nuevas** (`requests` ya está en
`backend/requirements.txt`) ni registra `rest_framework.authtoken` en
`INSTALLED_APPS` por defecto (token DRF solo lo usan las vistas opcionales).

## Qué se usa hoy en el SIGACU

La autenticación activa es **JWT** vía `apps.usuarios.services.AgaAuthClient`
(`POST /api/v1/auth/login/aga/`), que ya implementa el mismo contrato de red
(`AGA <token>`, `activeUser.personal_information`, `activeUser.account_info`).
El administrador de la UHO puede pasar el sistema a modo real cambiando solo el
`.env`:

```dotenv
AGA_AUTH_ENABLED=True
AGA_AUTH_MODE=real
AGA_AUTH_BASE_URL=https://auth.uho.edu.cu
AGA_AUTH_TOKEN=<token entregado por la UHO>
AGA_AUTH_ORIGIN=https://auth.uho.edu.cu
```

## Kit frontend (Vue/Pinia) — no aplicable

El kit también trae `frontend/{api.js,store.js,router-guard.js,Login.vue}` para
Vue 3 + Pinia. El SIGACU está hecho en **React 18 + Vite** y ya tiene su propio
cliente (`frontend/src/services/`) y su guardia de rutas
(`frontend/src/routes/`), así que esos archivos **no se copiaron**. Si algún
día se integra el kit en un proyecto Vue, seguir
`docs/INTEGRACION_UHO.md §4`.

Ver `docs/INTEGRACION_UHO.md` para el procedimiento completo.
