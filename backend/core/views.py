from datetime import timedelta

from django.db.models import Count, Prefetch
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ClimateLog, Greenhouse, HumidityCap, IrrigationCycle, Zone
from .serializers import (
    ClimateLogSerializer,
    GreenhouseSerializer,
    HumidityCapSerializer,
    IrrigationCycleSerializer,
    ZoneSerializer,
)
from .utils import east8_today


class GreenhouseViewSet(viewsets.ModelViewSet):
    queryset = Greenhouse.objects.annotate(zone_count=Count("zones")).all()
    serializer_class = GreenhouseSerializer


class ZoneViewSet(viewsets.ModelViewSet):
    serializer_class = ZoneSerializer

    def get_queryset(self):
        qs = (
            Zone.objects.select_related("greenhouse")
            .prefetch_related(
                Prefetch(
                    "humidity_caps",
                    queryset=HumidityCap.objects.filter(work_date=east8_today()),
                    to_attr="caps_today",
                )
            )
            .all()
        )
        greenhouse_id = self.request.query_params.get("greenhouseId")
        status = self.request.query_params.get("status")
        if greenhouse_id:
            qs = qs.filter(greenhouse_id=greenhouse_id)
        if status:
            qs = qs.filter(status=status)
        return qs


class ClimateLogViewSet(viewsets.ModelViewSet):
    serializer_class = ClimateLogSerializer

    def get_queryset(self):
        qs = ClimateLog.objects.select_related("zone", "zone__greenhouse").all()
        zone_id = self.request.query_params.get("zoneId")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        return qs


class HumidityCapViewSet(viewsets.ModelViewSet):
    serializer_class = HumidityCapSerializer

    def get_queryset(self):
        qs = HumidityCap.objects.select_related(
            "zone", "zone__greenhouse", "set_by"
        ).all()
        zone_id = self.request.query_params.get("zoneId")
        work_date = self.request.query_params.get("workDate")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        if work_date:
            qs = qs.filter(work_date=work_date)
        return qs

    def perform_create(self, serializer):
        serializer.save(set_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(set_by=self.request.user)


class IrrigationCycleViewSet(viewsets.ModelViewSet):
    serializer_class = IrrigationCycleSerializer

    def get_queryset(self):
        qs = IrrigationCycle.objects.select_related("zone", "zone__greenhouse").all()
        zone_id = self.request.query_params.get("zoneId")
        status = self.request.query_params.get("status")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        if status:
            qs = qs.filter(status=status)
        return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    now = timezone.now()
    since_24h = now - timedelta(hours=24)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    data = {
        "greenhouseCount": Greenhouse.objects.count(),
        "growingZoneCount": Zone.objects.filter(status=Zone.STATUS_GROWING).count(),
        "climateLogLast24h": ClimateLog.objects.filter(
            recorded_at__gte=since_24h
        ).count(),
        "irrigationScheduledToday": IrrigationCycle.objects.filter(
            status=IrrigationCycle.STATUS_SCHEDULED,
            start_at__gte=today_start,
            start_at__lt=today_end,
        ).count(),
        # 已设上限区数：今日（东八区自然日）设有湿度上限账的分区数，
        # 与分区列表中「今日湿度上限」非空的行数一致。
        "zonesWithCapToday": Zone.objects.filter(
            humidity_caps__work_date=east8_today()
        )
        .distinct()
        .count(),
    }
    return Response(data)
