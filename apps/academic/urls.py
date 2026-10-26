"""Rutas del módulo ``academic``."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.academic.views import AcademicPeriodViewSet, CourseViewSet, GradeRecordViewSet

app_name = "academic"

router = DefaultRouter()
router.register("academic_periods", AcademicPeriodViewSet, basename="academic_period")
router.register("courses", CourseViewSet, basename="course")
router.register("grade_records", GradeRecordViewSet, basename="grade_record")

urlpatterns = [path("", include(router.urls))]
