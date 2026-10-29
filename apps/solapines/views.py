"""Vistas del Solapín Digital."""

from __future__ import annotations

from django.http import HttpResponse
from django.utils import timezone as dj_timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.models import User
from apps.core.constants import AccessLevel, Role
from apps.core.mixins import AuditableModelViewSet
from apps.core.permissions import IsCredentialManager, IsSecurityDirector
from apps.core.utils import render_qr_png
from apps.solapines.compositor import compose_badge_image
from apps.solapines.models import Badge, BadgePrintJob, BadgeTemplate
from apps.solapines.serializers import (
    BadgeCancelSerializer,
    BadgeCreateSerializer,
    BadgeLevelUpdateSerializer,
    BadgePrintJobSerializer,
    BadgeSerializer,
    BadgeTemplateSerializer,
    BadgeVerifySerializer,
)
from apps.solapines.services import generar_solapin


class PNGRenderer(BaseRenderer):
    """Renderer binario para devolver imágenes sin serializarlas como JSON."""

    media_type = "image/png"
    format = "png"
    charset = None
    render_style = "binary"

    def render(self, data, media_type=None, renderer_context=None):
        return data


class BadgeTemplateViewSet(AuditableModelViewSet):
    """Configurador de plantillas del Solapín (RF-03.1 / RF-03.2)."""

    queryset = BadgeTemplate.objects.all()
    serializer_class = BadgeTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsSecurityDirector]
    filterset_fields = ["user_type", "campus", "is_default", "status"]
    search_fields = ["name"]
    lookup_field = "uuid"

    @extend_schema(summary="Plantilla por defecto del tipo de usuario", tags=["Solapín digital"])
    @action(detail=False, methods=["get"], url_path="default")
    def default(self, request):
        user_type = request.query_params.get("user_type")
        qs = self.get_queryset().filter(is_default=True)
        if user_type:
            qs = qs.filter(user_type=user_type)
        template = qs.first()
        if template is None:
            return Response({"detail": "No existe plantilla por defecto."}, status=404)
        return Response(self.get_serializer(template).data)


class BadgeViewSet(AuditableModelViewSet):
    """Gestión y búsqueda de solapines (RF-03.4 – RF-03.6)."""

    queryset = Badge.objects.select_related("user", "template")
    permission_classes = [permissions.IsAuthenticated, IsCredentialManager]
    filterset_fields = ["status", "access_level", "user__tipo_usuario", "user__campus_sede"]
    search_fields = [
        "badge_number",
        "user__ci",
        "user__nombres",
        "user__apellidos",
        "user__username",
    ]
    ordering_fields = ["issued_at", "user__apellidos", "status"]
    lookup_field = "uuid"

    def get_serializer_class(self):
        if self.action == "create":
            return BadgeCreateSerializer
        return BadgeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        badge = serializer.save(created_by=request.user, updated_by=request.user)
        return Response(BadgeSerializer(badge).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Solapines del usuario autenticado", tags=["Solapín digital"])
    def list(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.role in (Role.SUPERADMIN, Role.ADMIN)):
            # Consulta y administración de solapines: se limita al propio usuario
            # cuando el rol no pertenece al personal de seguridad.
            if request.user.role not in (
                Role.SECURITY_DIRECTOR,
                Role.SECURITY_OFFICER,
                Role.VISIT_APPROVER,
            ):
                qs = self.filter_queryset(self.get_queryset().filter(user=request.user))
                page = self.paginate_queryset(qs)
                if page is not None:
                    return self.get_paginated_response(self.get_serializer(page, many=True).data)
                return Response(self.get_serializer(qs, many=True).data)
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Cambiar nivel de acceso", tags=["Solapín digital"])
    @action(detail=True, methods=["post"], url_path="access-level")
    def update_access_level(self, request, uuid=None):
        badge = self.get_object()
        serializer = BadgeLevelUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        badge.access_level = serializer.validated_data["access_level"]
        badge.updated_by = request.user
        badge.save(update_fields=["access_level", "updated_by", "updated_at"])
        return Response(BadgeSerializer(badge).data)

    @extend_schema(summary="Cancelar solapín (DSP / SA)", tags=["Solapín digital"])
    @action(
        detail=True,
        methods=["post", "patch"],
        permission_classes=[permissions.IsAuthenticated, IsSecurityDirector],
    )
    def cancel(self, request, uuid=None):
        """``PATCH|POST /api/v1/solapines/{uuid}/cancel/`` → estado CANCELADO.

        Restringido al Director de Seguridad y Protección y al Superadministrador
        (RF-03.10 / RF-03.11).
        """
        badge = self.get_object()
        serializer = BadgeCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        badge.cancel(reason=serializer.validated_data["reason"], applied_by=request.user)
        return Response(BadgeSerializer(badge, context={"request": request}).data)

    @extend_schema(summary="Reactivar solapín", tags=["Solapín digital"])
    @action(detail=True, methods=["post"])
    def reactivate(self, request, uuid=None):
        badge = self.get_object()
        badge.status = Badge.Status.ACTIVE
        badge.updated_by = request.user
        badge.save(update_fields=["status", "updated_by", "updated_at"])
        return Response(BadgeSerializer(badge).data)

    @extend_schema(summary="Código QR del solapín (PNG)", tags=["Solapín digital"])
    @action(
        detail=True,
        methods=["get"],
        url_path="qr",
        permission_classes=[permissions.IsAuthenticated],
    )
    def qr(self, request, uuid=None):
        """Devuelve el QR en PNG: contiene sólo UUID + estado (RF-03.9).

        Cualquier usuario autenticado puede descargar **su propio** QR; el resto
        requiere el permiso de gestión de solapines.
        """
        badge = self.get_object()
        if badge.user_id != request.user.id and not IsCredentialManager().has_permission(
            request, self
        ):
            return Response(
                {"detail": "No tiene permiso para ver el QR de este solapín."},
                status=status.HTTP_403_FORBIDDEN,
            )
        response = HttpResponse(render_qr_png(badge.qr_payload), content_type="image/png")
        response["Content-Disposition"] = f'inline; filename="solapin-{badge.codigo_qr}.png"'
        return response

    @extend_schema(summary="Regenerar código QR", tags=["Solapín digital"])
    @action(detail=True, methods=["post"], url_path="rotate-qr")
    def rotate_qr(self, request, uuid=None):
        badge = self.get_object()
        token = badge.rotate_qr()
        return Response(
            {
                "qr_token": token,
                "codigo_qr": str(badge.codigo_qr),
                "badge_number": badge.badge_number,
            }
        )

    @extend_schema(summary="Renovar solapín", tags=["Solapín digital"])
    @action(detail=True, methods=["post"])
    def renew(self, request, uuid=None):
        badge = self.get_object()
        days = int(request.data.get("days", 365))
        badge.renew(days=days)
        return Response(BadgeSerializer(badge).data)

    @extend_schema(summary="Generar solapines en lote", tags=["Solapín digital"])
    @action(detail=False, methods=["post"], url_path="bulk-generate")
    def bulk_generate(self, request):
        """Crea solapines para todos los usuarios activos que no tengan uno."""
        filters = {
            "estado": True,
            "badges__isnull": True,
        }
        campus = request.data.get("campus")
        area = request.data.get("area")
        user_type = request.data.get("user_type")
        if campus:
            filters["campus_sede"] = campus
        if area:
            filters["area"] = area
        if user_type:
            filters["tipo_usuario"] = user_type

        template = BadgeTemplate.objects.filter(is_default=True).first()
        created = []
        for user in User.objects.filter(**filters):
            created.append(
                Badge.objects.create(
                    user=user,
                    template=template,
                    access_level=user.nivel_acceso or AccessLevel.LIMITED,
                    created_by=request.user,
                )
            )
        return Response(
            {"created": len(created), "badges": BadgeSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )


class MyBadgeView(APIView):
    """Solapín del usuario autenticado (RF-02.3 / RF-03).

    ``GET /api/v1/solapines/my-solapin/`` (alias ``my-badge/``).
    Si el usuario aún no tiene solapín, lo genera en ese momento con el nivel
    de acceso por defecto de su tipo (RF-03.7).
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Solapín del usuario autenticado", tags=["Solapín digital"])
    def get(self, request):
        badge, created = generar_solapin(request.user)
        data = BadgeSerializer(badge, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MyBadgeImageView(APIView):
    """Imagen final del Solapín del usuario autenticado (RF-02.3 / RF-03.3).

    ``GET /api/v1/solapines/mio/imagen/?download=1``

    Compone la plantilla asignada al solapín con los datos del usuario y su QR
    (UUID + estado). Devuelve ``image/png``; con ``download=1`` se sirve como
    adjunto para que el navegador lo descargue con un nombre legible.
    """

    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [PNGRenderer]

    @extend_schema(
        summary="Imagen compuesta del Solapín (PNG)",
        tags=["Solapín digital"],
        parameters=[
            OpenApiParameter(
                "download",
                OpenApiTypes.INT,
                enum=[0, 1],
                default=0,
                description="1 = forzar descarga como adjunto.",
            )
        ],
        responses={200: OpenApiTypes.BINARY},
    )
    def get(self, request):
        badge, created = generar_solapin(request.user)
        if created:
            badge = Badge.objects.select_related("user", "template").get(pk=badge.pk)

        png = compose_badge_image(badge)
        disposition = (
            "attachment" if request.query_params.get("download") in ("1", "true") else "inline"
        )
        filename = f"solapin-{badge.badge_number}.png"
        response = HttpResponse(png, content_type="image/png")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        response["Cache-Control"] = "private, max-age=60"
        return response


class BadgeVerificationView(APIView):
    """``POST /api/v1/solapines/verify/`` — valida un QR sin registrar acceso."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Verificar solapín", tags=["Solapín digital"])
    def post(self, request):
        serializer = BadgeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        qs = Badge.objects.select_related("user", "template")
        if data.get("qr_token"):
            qs = qs.filter(qr_token=data["qr_token"])
        elif data.get("badge_number"):
            qs = qs.filter(badge_number__iexact=data["badge_number"])
        else:
            qs = qs.filter(user__ci=data["identity_card"])

        badge = qs.order_by("-issued_at").first()
        if badge is None:
            return Response(
                {"valid": False, "reason": "NO_ENCONTRADO", "message": "Solapín no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not badge.is_valid:
            return Response(
                {
                    "valid": False,
                    "reason": badge.status,
                    "message": "El solapín no está vigente.",
                    "badge": BadgeSerializer(badge).data,
                }
            )

        return Response({"valid": True, "badge": BadgeSerializer(badge).data})


class BadgePrintJobViewSet(AuditableModelViewSet):
    """Lotes de impresión / generación masiva de solapines."""

    queryset = BadgePrintJob.objects.all()
    serializer_class = BadgePrintJobSerializer
    permission_classes = [permissions.IsAuthenticated, IsCredentialManager]
    http_method_names = ["get", "post", "head", "options"]
    lookup_field = "uuid"

    def perform_create(self, serializer):
        job = serializer.save(created_by=self.request.user)
        total = User.objects.filter(
            estado=True,
            tipo_usuario=job.user_type or None,
            campus_sede=job.campus or None,
            area=job.area or None,
        ).count()
        job.total = total
        job.save(update_fields=["total"])

    @extend_schema(summary="Registrar solapín para visitante", tags=["Solapín digital"])
    @action(detail=False, methods=["post"], url_path="visitor")
    def visitor(self, request):
        """Crea un solapín temporal para un visitante (RF-03.7)."""
        from apps.visitors.models import Visitor

        visitor_id = request.data.get("visitor_id")
        visitor = Visitor.objects.filter(uuid=visitor_id).first()
        if visitor is None:
            return Response({"detail": "Visitante no encontrado."}, status=404)

        badge = Badge.objects.create(
            user=visitor.user,
            access_level=AccessLevel.VISITOR,
            valid_from=visitor.valid_from,
            valid_until=visitor.valid_until,
            expires_at=(
                dj_timezone.make_aware(
                    dj_timezone.datetime.combine(
                        visitor.valid_until, dj_timezone.datetime.max.time()
                    )
                )
                if visitor.valid_until
                else None
            ),
            created_by=request.user,
            notes=f"Visitante temporal · Solicitud {visitor.visit_request.uuid}",
        )
        return Response(BadgeSerializer(badge).data, status=status.HTTP_201_CREATED)
