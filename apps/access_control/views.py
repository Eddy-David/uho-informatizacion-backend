"""Vistas del control de acceso."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control.models import AccessLog
from apps.access_control.serializers import (
    AccessLogSerializer,
    AccessRegisterSerializer,
    AccessVerificationRequestSerializer,
    AccessVerificationResponseSerializer,
    AccessVerifyResultSerializer,
    AccessVerifySerializer,
    SyncAccessLogItemSerializer,
)
from apps.access_control.services import (
    DenialReason,
    datos_persona,
    verificar_acceso,
    verify_access,
)
from apps.core.catalogs import AccessPoint, CampusSite
from apps.solapines.models import Badge
from apps.core.constants import MovementType
from apps.core.exports import export_to_excel, export_to_pdf
from apps.core.permissions import IsAccessOperator


class AccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Bitácora de accesos: solo lectura (RF-04.5 / RF-08.1)."""

    queryset = AccessLog.objects.select_related("access_point", "registered_by")
    serializer_class = AccessLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]
    filterset_fields = ["result", "movement", "campus", "channel", "user_type", "access_point"]
    search_fields = ["full_name", "identity_card"]
    ordering_fields = ["occurred_at", "full_name"]
    lookup_field = "uuid"

    @extend_schema(
        summary="Registrar movimiento en el punto de control",
        request=AccessRegisterSerializer,
        responses={201: AccessLogSerializer},
        tags=["Control de acceso"],
    )
    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        """``POST /api/v1/access_control/register/`` (RF-04.5).

        Ejecuta el motor y guarda el movimiento. Si el motor deniega, se guarda
        igualmente el intento (``DENEGADO``) pero se responde 403.
        """
        serializer = AccessRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        badge = Badge.all_objects.filter(codigo_qr=data["solapin"]).first()
        if badge is None:
            badge = Badge.all_objects.filter(uuid=data["solapin"]).first()
        if badge is None:
            return Response(
                {"detail": "Solapín no encontrado.", "reason": DenialReason.NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )

        sede = None
        if data.get("sede"):
            sede = CampusSite.objects.filter(uuid=data["sede"]).first()
            if sede is None:
                return Response(
                    {"detail": "Sede no encontrada."}, status=status.HTTP_400_BAD_REQUEST
                )

        access_point = None
        if data.get("punto_control"):
            access_point = AccessPoint.objects.filter(uuid=data["punto_control"]).first()

        result = verify_access(
            operator=request.user,
            movement=data["tipo_movimiento"],
            qr_token=str(badge.codigo_qr),
            campus=sede.code if sede else "",
            access_point=access_point,
            channel=data.get("canal") or AccessLog.Channel.WEB,
            request=request,
            observed=data.get("observaciones", ""),
        )
        if result.log is not None:
            result.log.sede = sede
            result.log.save(update_fields=["sede"])

        payload = AccessLogSerializer(result.log).data
        return Response(
            payload,
            status=status.HTTP_201_CREATED if result.allowed else status.HTTP_403_FORBIDDEN,
        )

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(occurred_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(occurred_at__date__lte=date_to)
        return qs

    @extend_schema(summary="Exportar bitácora a Excel", tags=["Control de acceso"])
    @action(detail=False, methods=["get"], url_path="export/excel")
    def export_excel(self, request):
        logs = self.filter_queryset(self.get_queryset())[:10000]
        return export_to_excel(
            title="Bitácora de accesos",
            sheet_name="Accesos",
            headers=[
                "Fecha y hora",
                "Nombre",
                "CI",
                "Sede",
                "Punto",
                "Movimiento",
                "Resultado",
                "Motivo",
                "Registrado por",
            ],
            rows=[
                (
                    timezone.localtime(log.occurred_at).replace(tzinfo=None),
                    log.full_name,
                    log.identity_card,
                    log.campus,
                    log.access_point.name if log.access_point else "",
                    log.movement,
                    log.result,
                    log.denial_reason,
                    log.registered_by.nombre_completo if log.registered_by else "",
                )
                for log in logs
            ],
            metadata={"Registros exportados": len(logs)},
        )

    @extend_schema(summary="Exportar bitácora a PDF", tags=["Control de acceso"])
    @action(detail=False, methods=["get"], url_path="export/pdf")
    def export_pdf(self, request):
        logs = self.filter_queryset(self.get_queryset())[:2000]
        return export_to_pdf(
            title="Bitácora de accesos",
            context={
                "headers": ["Fecha", "Nombre", "CI", "Sede", "Movimiento", "Resultado"],
                "rows": [
                    [
                        timezone.localtime(log.occurred_at).strftime("%Y-%m-%d %H:%M"),
                        log.full_name,
                        log.identity_card,
                        log.campus,
                        log.get_movement_display(),
                        log.get_result_display(),
                    ]
                    for log in logs
                ],
                "filters": {k: v for k, v in request.query_params.items()},
            },
        )

    @extend_schema(summary="Estadísticas de accesos", tags=["Control de acceso"])
    @action(detail=False, methods=["get"])
    def stats(self, request):
        today = timezone.localtime().date()
        qs = AccessLog.objects.filter(occurred_at__date=today)
        by_hour = {
            str(item["occurred_at__hour"]): item["total"]
            for item in qs.values("occurred_at__hour").annotate(total=Count("id"))
        }
        by_campus = {
            item["campus"] or "SIN_SEDE": item["total"]
            for item in qs.values("campus").annotate(total=Count("id"))
        }
        by_type = {
            item["user_type"] or "DESCONOCIDO": item["total"]
            for item in qs.values("user_type").annotate(total=Count("id"))
        }
        return Response(
            {
                "date": today,
                "total": qs.count(),
                "granted": qs.filter(result=AccessLog.Result.GRANTED).count(),
                "denied": qs.filter(result=AccessLog.Result.DENIED).count(),
                "by_campus": by_campus,
                "by_hour": by_hour,
                "by_user_type": by_type,
            }
        )


class VerifyAccessControlView(APIView):
    """``POST /api/v1/access_control/verify/`` — motor de verificación (RF-04).

    Recibe ``{"identificador": "<UUID del QR> o <CI>"}``, aplica las reglas de
    negocio y **no** registra el movimiento: la respuesta indica si se permite
    el paso y los datos de la ficha (RF-04.3).
    """

    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]

    @extend_schema(
        summary="Verificar acceso (UUID del QR o CI)",
        request=AccessVerifySerializer,
        responses={200: AccessVerifyResultSerializer},
        tags=["Control de acceso"],
    )
    def post(self, request):
        serializer = AccessVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identificador = serializer.validated_data["identificador"]

        result = verificar_acceso(identificador)
        payload = {
            "permitido": result.allowed,
            "razon": result.reason or "OK",
            "mensaje": result.message,
            "datos_persona": datos_persona(result.user, result.badge),
            "solapin": (
                {
                    "uuid": str(result.badge.uuid),
                    "codigo_qr": str(result.badge.codigo_qr),
                    "numero": result.badge.badge_number,
                    "estado": result.badge.status,
                    "nivel_acceso": result.badge.access_level,
                    "fecha_expiracion": result.badge.expires_at,
                }
                if result.badge is not None
                else None
            ),
        }
        return Response(payload, status=status.HTTP_200_OK)


class VerifyAccessView(APIView):
    """``POST /api/v1/access/verify/`` — verificación y registro del movimiento."""

    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]

    @extend_schema(
        summary="Verificar acceso (QR, solapín o CI)",
        request=AccessVerificationRequestSerializer,
        responses={200: AccessVerificationResponseSerializer},
        tags=["Control de acceso"],
    )
    def post(self, request):
        serializer = AccessVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        access_point = None
        if data.get("access_point"):
            access_point = AccessPoint.objects.filter(uuid=data["access_point"]).first()

        result = verify_access(
            operator=request.user,
            movement=data["movement"],
            qr_token=data.get("qr_token", ""),
            badge_number=data.get("badge_number", ""),
            identity_card=data.get("identity_card", ""),
            campus=data.get("campus", ""),
            access_point=access_point,
            channel=data["channel"],
            request=request,
            client_uuid=data.get("client_uuid"),
            device_info=data.get("device_info", ""),
            observed=data.get("observed", ""),
        )

        from apps.solapines.serializers import BadgeSerializer

        payload = {
            "allowed": result.allowed,
            "reason": result.reason,
            "message": result.message,
            "badge": BadgeSerializer(result.badge).data if result.badge else None,
            "log": AccessLogSerializer(result.log).data if result.log else None,
        }
        return Response(payload, status=status.HTTP_200_OK)


class SyncOfflineAccessView(APIView):
    """``POST /api/v1/access/sync/`` — sincroniza la cola offline de la PWA.

    Recibe una lista de registros verificados sin conexión y los replica en el
    servidor respetando ``client_uuid`` para evitar duplicados (RNF-09).
    """

    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]

    @extend_schema(
        summary="Sincronizar registros offline",
        request=SyncAccessLogItemSerializer(many=True),
        tags=["Control de acceso"],
    )
    def post(self, request):
        items = request.data if isinstance(request.data, list) else request.data.get("items", [])
        serializer = SyncAccessLogItemSerializer(data=items, many=True)
        serializer.is_valid(raise_exception=True)

        created, skipped = 0, 0
        for item in serializer.validated_data:
            if AccessLog.objects.filter(client_uuid=item["client_uuid"]).exists():
                skipped += 1
                continue
            access_point = (
                AccessPoint.objects.filter(uuid=item["access_point"]).first()
                if item.get("access_point")
                else None
            )
            verify_access(
                operator=request.user,
                movement=item["movement"],
                qr_token=item.get("qr_token", ""),
                badge_number=item.get("badge_number", ""),
                identity_card=item.get("identity_card", ""),
                campus=item.get("campus", ""),
                access_point=access_point,
                channel=AccessLog.Channel.PWA,
                request=request,
                client_uuid=item["client_uuid"],
                device_info=item.get("device_info", ""),
                observed=item.get("observed", ""),
            )
            created += 1

        return Response({"created": created, "skipped": skipped})


class CurrentlyInsideView(APIView):
    """``GET /api/v1/access/inside/`` — personas actualmente dentro del campus."""

    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]

    @extend_schema(summary="Personas actualmente dentro", tags=["Control de acceso"])
    def get(self, request):
        since = timezone.localtime() - timedelta(hours=24)
        qs = AccessLog.objects.filter(
            result=AccessLog.Result.GRANTED, occurred_at__gte=since
        ).order_by("-occurred_at")
        last_by_person: dict[str, AccessLog] = {}
        for log in qs:
            key = log.identity_card or log.full_name
            if key and key not in last_by_person:
                last_by_person[key] = log
        inside = [log for log in last_by_person.values() if log.movement == MovementType.ENTRY]
        return Response(
            {
                "count": len(inside),
                "people": AccessLogSerializer(inside[:200], many=True).data,
            }
        )
