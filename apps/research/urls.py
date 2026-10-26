"""Rutas del módulo ``research``."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.research.views import ProjectMilestoneViewSet, ResearchProjectViewSet

app_name = "research"

router = DefaultRouter()
router.register("research_projects", ResearchProjectViewSet, basename="research_project")
router.register("project_milestones", ProjectMilestoneViewSet, basename="project_milestone")

urlpatterns = [path("", include(router.urls))]
