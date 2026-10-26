"""Vistas del módulo de visitantes."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import Role, UserType
from apps.core.mixins import AuditableModelViewSet
from apps.core.permissions import IsVisitApprover
from apps.notifications.services import notify_user
from apps.visitors.models import Visitor, VisitRequest
from apps.visitors.serializers import (
    VisitorSerializer,
    VisitRequestSerializer,
    VisitReviewSerializer,
)


class VisitRequestViewSet(AuditableModelViewSet):
    """Solicitudes de visita (creación por cuadros, revisión por aprobadores)."""

    queryset = VisitRequest.objects.select_related("requester", "reviewer")
    serializer_class = VisitRequestSerializer
    filterset_fields = ["status", "campus", "area"]
    search_fields = ["visitor_name", "visitor_identity_card", "code", "requester__nombres"]
    ordering_fields = ["created_at", "valid_from", "status"]
    lookup_field = "uuid"

    def get_permissions(self):
        if self.action in ("approve", "reject", "request_changes", "pending"):
            return [permissions.IsAuthenticated(), IsVisitApprover()]
        if self.action in ("create",):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if self.action in ("approve", "reject", "request_changes", "pending"):
            return qs
        if user.is_superuser or user.role in (
            Role.SUPERADMIN,
            Role.ADMIN,
            Role.SECURITY_DIRECTOR,
            Role.SECURITY_OFFICER,
            Role.VISIT_APPROVER,
        ):
            return qs
        # Un cuadro solo ve sus propias solicitudes.
        return qs.filter(requester=user)

    def perform_create(self, serializer):
        request_obj = serializer.save(requester=self.request.user, created_by=self.request.user)
        for approver in self._approvers():
            notify_user(
                approver,
                title="Nueva solicitud de visita",
                message=f"{request_obj.requester.nombre_completo} solicitó visita para "
                f"{request_obj.visitor_name} ({request_obj.code}).",
                category="VISITA",
                link=f"/visitors/requests/{request_obj.uuid}",
                payload={"visit_request": str(request_obj.uuid)},
            )

    @staticmethod
    def _approvers():
        from apps.usuarios.models import User

        return User.objects.filter(
            role__in=(Role.VISIT_APPROVER, Role.SECURITY_DIRECTOR), estado=True
        )

    @extend_schema(summary="Bandeja de solicitudes pendientes", tags=["Visitantes"])
    @action(detail=False, methods=["get"])
    def pending(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(status=VisitRequest.Status.PENDING))
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @extend_schema(summary="Aprobar solicitud", request=VisitReviewSerializer, tags=["Visitantes"])
    @action(detail=True, methods=["post"])
    def approve(self, request, uuid=None):
        visit = self.get_object()
        serializer = VisitReviewSerializer(data={**request.data, "action": "approve"})
        serializer.is_valid(raise_exception=True)
        visitor = visit.approve(request.user, serializer.validated_data.get("comment", ""))
        visitor = self._ensure_visitor_user(visitor)

        from apps.solapines.models import Badge

        Badge.objects.create(
            user=visitor.user,
            access_level="VISITANTE",
            valid_from=visitor.valid_from,
            valid_until=visitor.valid_until,
            created_by=request.user,
            notes=f"Solapín temporal · {visit.code}",
        )
        notify_user(
            visit.requester,
            title="Solicitud de visita aprobada",
            message=f"La solicitud {visit.code} para {visit.visitor_name} fue aprobada.",
            category="VISITA",
            link=f"/visitors/requests/{visit.uuid}",
        )
        return Response(VisitRequestSerializer(visit).data)

    @extend_schema(summary="Rechazar solicitud", request=VisitReviewSerializer, tags=["Visitantes"])
    @action(detail=True, methods=["post"])
    def reject(self, request, uuid=None):
        visit = self.get_object()
        serializer = VisitReviewSerializer(data={**request.data, "action": "reject"})
        serializer.is_valid(raise_exception=True)
        visit.reject(request.user, serializer.validated_data["comment"])
        notify_user(
            visit.requester,
            title="Solicitud de visita rechazada",
            message=f"La solicitud {visit.code} fue rechazada: {visit.review_comment}",
            category="VISITA",
            link=f"/visitors/requests/{visit.uuid}",
        )
        return Response(VisitRequestSerializer(visit).data)

    @extend_schema(
        summary="Solicitar cambios en la solicitud",
        request=VisitReviewSerializer,
        tags=["Visitantes"],
    )
    @action(detail=True, methods=["post"], url_path="request-changes")
    def request_changes(self, request, uuid=None):
        visit = self.get_object()
        serializer = VisitReviewSerializer(data={**request.data, "action": "request_changes"})
        serializer.is_valid(raise_exception=True)
        visit.request_changes(request.user, serializer.validated_data["comment"])
        notify_user(
            visit.requester,
            title="Cambios solicitados en su visita",
            message=f"La solicitud {visit.code} requiere cambios: {visit.review_comment}",
            category="VISITA",
            link=f"/visitors/requests/{visit.uuid}",
        )
        return Response(VisitRequestSerializer(visit).data)

    @staticmethod
    def _ensure_visitor_user(visitor: Visitor):
        if visitor.user_id:
            return visitor
        from apps.usuarios.models import User

        probable_username = f"visitante.{visitor.identity_card[-6:]}"
        user, created = User.objects.get_or_create(
            username=probable_username,
            defaults={
                "nombres": visitor.full_name.split(" ")[0],
                "apellidos": " ".join(visitor.full_name.split(" ")[1:]) or "Visitante",
                "ci": visitor.identity_card,
                "tipo_usuario": UserType.VISITOR,
                "role": Role.USER,
                "nivel_acceso": "VISITANTE",
                "campus_sede": visitor.campus,
                "area": visitor.area,
                "estado": True,
                "sync_source": "LOCAL",
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        visitor.user = user
        visitor.save(update_fields=["user", "updated_at"])
        return visitor


class VisitorViewSet(viewsets.ReadOnlyModelViewSet):
    """Visitantes registrados y su estado de permanencia."""

    queryset = Visitor.objects.select_related("visit_request", "host_user")
    serializer_class = VisitorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["campus", "area"]
    search_fields = ["full_name", "identity_card"]
    lookup_field = "uuid"

    @extend_schema(summary="Visitantes presentes en el campus", tags=["Visitantes"])
    @action(detail=False, methods=["get"], url_path="inside")
    def inside(self, request):
        qs = self.get_queryset().filter(checked_in_at__isnull=False, checked_out_at__isnull=True)
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(summary="Check-out de visitante", tags=["Visitantes"])
    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, uuid=None):
        visitor = self.get_object()
        visitor.checked_out_at = timezone.now()
        visitor.save(update_fields=["checked_out_at", "updated_at"])
        return Response(self.get_serializer(visitor).data)


class MyVisitRequestsView(APIView):
    """``GET /api/v1/visitors/my-requests/`` — solicitudes del usuario autenticado."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Mis solicitudes de visita", tags=["Visitantes"])
    def get(self, request):
        qs = VisitRequest.objects.filter(
            Q(requester=request.user) | Q(visitor_identity_card=request.user.ci)
        ).distinct()
        return Response(VisitRequestSerializer(qs, many=True).data)
