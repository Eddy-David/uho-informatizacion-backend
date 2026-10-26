"""Rutas de auditoría: consulta inmutable y catálogo de permisos."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.audit_api import AuditEventViewSet, PermissionMatrixView

app_name = "audit"

router = DefaultRouter()
router.register("events", AuditEventViewSet, basename="audit-event")

urlpatterns = [
    path("permissions/", PermissionMatrixView.as_view(), name="permissions"),
    path("", include(router.urls)),
]
