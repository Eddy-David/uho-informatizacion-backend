"""Rutas del módulo ``students``."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.students.views import EnrollmentViewSet, StudentProfileViewSet

app_name = "students"

router = DefaultRouter()
router.register("student_profiles", StudentProfileViewSet, basename="student_profile")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")

urlpatterns = [path("", include(router.urls))]
