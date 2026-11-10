"""Rutas del módulo de visitantes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.visitors.views import MyVisitRequestsView, VisitorViewSet, VisitRequestViewSet

app_name = "visitors"

router = DefaultRouter()
router.register("requests", VisitRequestViewSet, basename="visit-request")
router.register("visitors", VisitorViewSet, basename="visitor")

urlpatterns = [
    # Rutas canónicas (inglés): requests/, pending/, approve/, reject/, etc.
    # El frontend las consume vía `visitorService`. El endpoint en español
    # equivalente a `PATCH {id}/estado/` es `PATCH requests/{uuid}/estado/`.
    path("", include(router.urls)),
    path("my-requests/", MyVisitRequestsView.as_view(), name="my-requests"),
]
