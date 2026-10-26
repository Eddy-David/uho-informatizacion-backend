"""Rutas del módulo ``hr``."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.hr.views import EmployeeRecordViewSet, LeaveRequestViewSet, PositionViewSet

app_name = "hr"

router = DefaultRouter()
router.register("positions", PositionViewSet, basename="position")
router.register("employee_records", EmployeeRecordViewSet, basename="employee_record")
router.register("leave_requests", LeaveRequestViewSet, basename="leave_request")

urlpatterns = [path("", include(router.urls))]
