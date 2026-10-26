"""Vistas del módulo de vehículos."""

from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import MovementType
from apps.core.mixins import AuditableModelViewSet
from apps.core.permissions import IsAccessOperator, ReadOnlyOrAdmin
from apps.vehicles.models import AuthorizedVehicle, VehicleMovement
from apps.vehicles.serializers import (
    AuthorizedVehicleSerializer,
    RegisterMovementSerializer,
    VehicleCheckSerializer,
    VehicleMovementSerializer,
)


class AuthorizedVehicleViewSet(AuditableModelViewSet):
    """Catálogo de vehículos autorizados."""

    queryset = AuthorizedVehicle.objects.all()
    serializer_class = AuthorizedVehicleSerializer
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrAdmin]
    filterset_fields = ["campus", "vehicle_type", "is_active"]
    search_fields = ["plate", "owner_name", "brand", "model"]
    ordering_fields = ["plate", "owner_name", "valid_until"]
    lookup_field = "uuid"

    def perform_create(self, serializer):
        serializer.save(approved_by=self.request.user, created_by=self.request.user)


class VehicleMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """Movimientos vehiculares (solo lectura; se crean con ``register``)."""

    queryset = VehicleMovement.objects.all()
    serializer_class = VehicleMovementSerializer
    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]
    filterset_fields = ["campus", "movement", "authorized", "is_exception"]
    search_fields = ["plate", "driver_name"]
    lookup_field = "uuid"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("today") in ("1", "true", "yes"):
            qs = qs.filter(occurred_at__date=timezone.localdate())
        return qs


class VehicleCheckView(APIView):
    """``GET /api/v1/vehicles/check/?plate=...`` — ¿está autorizado?"""

    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]

    @extend_schema(summary="Verificar placa autorizada", tags=["Vehículos"])
    def get(self, request):
        serializer = VehicleCheckSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        plate = serializer.validated_data["plate"].strip().upper()
        vehicle = AuthorizedVehicle.objects.filter(plate=plate).first()
        if vehicle and vehicle.is_valid:
            return Response(
                {
                    "found": True,
                    "authorized": True,
                    "vehicle": AuthorizedVehicleSerializer(vehicle).data,
                }
            )
        if vehicle:
            return Response(
                {
                    "found": True,
                    "authorized": False,
                    "reason": "Vigencia expirada o desactivado",
                    "vehicle": AuthorizedVehicleSerializer(vehicle).data,
                }
            )
        return Response({"found": False, "authorized": False, "plate": plate, "vehicle": None})


class RegisterVehicleMovementView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]

    @extend_schema(
        summary="Registrar movimiento vehicular",
        request=RegisterMovementSerializer,
        responses={201: VehicleMovementSerializer},
        tags=["Vehículos"],
    )
    def post(self, request):
        serializer = RegisterMovementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        plate = data["plate"].strip().upper()
        vehicle = AuthorizedVehicle.objects.filter(plate=plate).first()
        authorized = bool(vehicle and vehicle.is_valid)

        from apps.core.catalogs import AccessPoint

        access_point = (
            AccessPoint.objects.filter(uuid=data["access_point"]).first()
            if data.get("access_point")
            else None
        )
        status_after = (
            VehicleMovement.Status.INSIDE
            if data["movement"] == MovementType.ENTRY
            else VehicleMovement.Status.OUTSIDE
        )
        movement = VehicleMovement.objects.create(
            vehicle=vehicle,
            plate=plate,
            vehicle_type=data.get("vehicle_type") or (vehicle.vehicle_type if vehicle else ""),
            driver_name=data.get("driver_name", ""),
            driver_identity_card=data.get("driver_identity_card", ""),
            campus=data.get("campus", ""),
            access_point=access_point,
            movement=data["movement"],
            authorized=authorized,
            is_exception=data["movement"] == MovementType.ENTRY and not authorized,
            reason=data.get("reason", ""),
            status_after=status_after,
            registered_by=request.user,
            occurred_at=timezone.now(),
        )
        return Response(VehicleMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class VehicleTypesView(APIView):
    """``GET /api/v1/vehicles/types/`` — nomenclador de tipos de vehículo."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Tipos de vehículo", tags=["Vehículos"])
    def get(self, request):
        from apps.core.catalogs import CatalogEntry

        types = CatalogEntry.objects.filter(
            kind=CatalogEntry.Kind.VEHICLE_TYPE, is_active=True
        ).values("code", "name")
        if not types:
            types = [
                {"code": "AUTOMOVIL", "name": "Automóvil"},
                {"code": "MOTOCICLETA", "name": "Motocicleta"},
                {"code": "OMNIBUS", "name": "Ómnibus"},
                {"code": "CAMION", "name": "Camión"},
                {"code": "BICICLETA", "name": "Bicicleta"},
            ]
        return Response(list(types))
