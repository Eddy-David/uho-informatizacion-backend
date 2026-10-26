"""
Rutas raíz del proyecto UHO SIGACU.

Esquema de URLs::

    /admin/                      → Administración Django
    /api/v1/                     → API REST (versionada)
    /api/docs/                   → Swagger UI
    /api/schema/                 → Esquema OpenAPI (YAML)
    /oauth/                      → Endpoints OAuth2 (django-oauth-toolkit)
    /ws/notifications/           → WebSocket de notificaciones (Channels)
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.core.urls import AboutView, HealthCheckView

admin.site.site_header = f"{settings.INSTITUTION_NAME} · SIGACU"
admin.site.site_title = "SIGACU"
admin.site.index_title = "Administración del sistema"

api_v1_patterns = [
    path("auth/", include("apps.usuarios.urls")),
    path("catalogs/", include("apps.core.urls")),
    path("core/catalogs/", include("apps.core.catalog_urls")),
    # Nomencladores básicos de RF-09.3 con nombres en español
    path("nomencladores/", include("apps.core.nomencladores_urls")),
    path("access/", include("apps.access_control.urls")),
    # Motor de verificación y registro (RF-04), prefijo oficial en español
    path("access_control/", include("apps.access_control.access_control_urls")),
    path("solapines/", include("apps.solapines.urls")),
    path("visitors/", include("apps.visitors.urls")),
    path("vehicles/", include("apps.vehicles.urls")),
    path("incidents/", include("apps.incidents.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("reports/", include("apps.reports.urls")),
    path("audit/", include("apps.core.audit_urls")),
    # Módulos universitarios futuros (esqueleto expandible)
    path("students/", include("apps.students.urls")),
    path("academic/", include("apps.academic.urls")),
    path("hr/", include("apps.hr.urls")),
    path("maintenance/", include("apps.maintenance.urls")),
    path("research/", include("apps.research.urls")),
    path("analytics/", include("apps.analytics.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/v1/about/", AboutView.as_view(), name="about"),
    path("api/v1/", include((api_v1_patterns, "v1"), namespace="v1")),
    # Documentación interactiva
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # OAuth2
    path("oauth/", include("oauth2_provider.urls", namespace="oauth2_provider")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
