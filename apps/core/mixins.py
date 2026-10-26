"""Mixins compartidos por las vistas de la API."""

from __future__ import annotations

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


class AuditableModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet que registra automáticamente el usuario de creación/edición."""

    def perform_create(self, serializer):
        extra = {}
        model = serializer.Meta.model
        if hasattr(model, "created_by"):
            extra["created_by"] = self.request.user
        if hasattr(model, "updated_by"):
            extra["updated_by"] = self.request.user
        serializer.save(**extra)

    def perform_update(self, serializer):
        extra = {}
        if hasattr(serializer.Meta.model, "updated_by"):
            extra["updated_by"] = self.request.user
        serializer.save(**extra)


class SoftDeleteDestroyMixin:
    """Convierte DELETE en una eliminación lógica cuando el modelo lo soporta."""

    def perform_destroy(self, instance):
        if hasattr(instance, "is_deleted"):
            instance.delete()
        else:
            instance.delete()


class CatalogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD completo para nomencladores simples."""


class ChoicesViewMixin:
    """Expone las opciones de un ``TextChoices`` mediante ``GET .../choices/``."""

    choices_map: dict[str, type] = {}

    @action(detail=False, methods=["get"], url_path="choices")
    def choices(self, request):
        return Response(
            {
                name: [{"value": value, "label": str(label)} for value, label in enum.choices]
                for name, enum in self.choices_map.items()
            }
        )
