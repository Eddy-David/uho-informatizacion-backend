"""Rutas del Solapín Digital."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.solapines.views import (
    BadgePrintJobViewSet,
    BadgeTemplateViewSet,
    BadgeVerificationView,
    BadgeViewSet,
    MyBadgeImageView,
    MyBadgeView,
)

app_name = "solapines"

router = DefaultRouter()
router.register("templates", BadgeTemplateViewSet, basename="badge-template")
router.register("badges", BadgeViewSet, basename="badge")
router.register("print-jobs", BadgePrintJobViewSet, basename="badge-print-job")

urlpatterns = [
    # RF-03: nombre oficial del endpoint; my-badge/ se conserva por compatibilidad.
    path("my-solapin/", MyBadgeView.as_view(), name="my-solapin"),
    path("my-badge/", MyBadgeView.as_view(), name="my-badge"),
    # RF-02.3: ruta oficial consumida por el frontend (SolapinCard).
    path("mio/", MyBadgeView.as_view(), name="my-solapin-mio"),
    # RF-03.3: imagen final compuesta (plantilla + datos + QR).
    path("mio/imagen/", MyBadgeImageView.as_view(), name="my-badge-image"),
    path("verify/", BadgeVerificationView.as_view(), name="verify"),
    path("", include(router.urls)),
]
