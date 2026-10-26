"""Rutas del control de acceso."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.access_control.views import (
    AccessLogViewSet,
    CurrentlyInsideView,
    SyncOfflineAccessView,
    VerifyAccessView,
)

app_name = "access_control"

router = DefaultRouter()
router.register("logs", AccessLogViewSet, basename="access-log")

urlpatterns = [
    path("verify/", VerifyAccessView.as_view(), name="verify"),
    path("sync/", SyncOfflineAccessView.as_view(), name="sync-offline"),
    path("inside/", CurrentlyInsideView.as_view(), name="inside"),
    path("", include(router.urls)),
]
