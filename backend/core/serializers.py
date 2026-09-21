from rest_framework import serializers

from .models import (
    ClimateLog,
    Greenhouse,
    HumidityCap,
    IrrigationCycle,
    Zone,
    east8_date,
    east8_today,
)


class GreenhouseSerializer(serializers.ModelSerializer):
    areaM2 = serializers.DecimalField(
        source="area_m2", max_digits=10, decimal_places=2
    )
    zoneCount = serializers.SerializerMethodField()

    class Meta:
        model = Greenhouse
        fields = (
            "id",
            "name",
            "location",
            "areaM2",
            "notes",
            "zoneCount",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "zoneCount", "created_at", "updated_at")

    def get_zoneCount(self, obj):
        if hasattr(obj, "zone_count"):
            return obj.zone_count
        return obj.zones.count()


class ZoneSerializer(serializers.ModelSerializer):
    greenhouseId = serializers.PrimaryKeyRelatedField(
        source="greenhouse", queryset=Greenhouse.objects.all()
    )
    zoneCode = serializers.CharField(source="zone_code")
    cropName = serializers.CharField(source="crop_name", allow_blank=True, required=False)
    greenhouseName = serializers.CharField(source="greenhouse.name", read_only=True)
    todayCapPct = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = (
            "id",
            "greenhouseId",
            "greenhouseName",
            "zoneCode",
            "cropName",
            "status",
            "todayCapPct",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "greenhouseName",
            "todayCapPct",
            "created_at",
            "updated_at",
        )

    def get_todayCapPct(self, obj):
        """当天（东八区自然日）的湿度上限；未设返回 None。"""
        today = east8_today()
        for cap in obj.humidity_caps.all():
            if cap.work_date == today:
                return cap.cap_pct
        return None

    def validate(self, attrs):
        greenhouse = attrs.get("greenhouse") or getattr(self.instance, "greenhouse", None)
        zone_code = attrs.get("zone_code") or getattr(self.instance, "zone_code", None)
        if greenhouse and zone_code:
            qs = Zone.objects.filter(greenhouse=greenhouse, zone_code=zone_code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"zoneCode": "同一温室内分区编码必须唯一"}
                )
        return attrs


class ClimateLogSerializer(serializers.ModelSerializer):
    zoneId = serializers.PrimaryKeyRelatedField(
        source="zone", queryset=Zone.objects.all()
    )
    recordedAt = serializers.DateTimeField(source="recorded_at")
    tempC = serializers.DecimalField(source="temp_c", max_digits=5, decimal_places=2)
    humidityPct = serializers.DecimalField(
        source="humidity_pct", max_digits=5, decimal_places=2
    )
    parUmol = serializers.DecimalField(
        source="par_umol", max_digits=8, decimal_places=2, required=False
    )
    co2Ppm = serializers.DecimalField(
        source="co2_ppm", max_digits=8, decimal_places=2, required=False
    )
    zoneCode = serializers.CharField(source="zone.zone_code", read_only=True)
    greenhouseName = serializers.CharField(
        source="zone.greenhouse.name", read_only=True
    )

    class Meta:
        model = ClimateLog
        fields = (
            "id",
            "zoneId",
            "zoneCode",
            "greenhouseName",
            "recordedAt",
            "tempC",
            "humidityPct",
            "parUmol",
            "co2Ppm",
            "created_at",
        )
        read_only_fields = ("id", "zoneCode", "greenhouseName", "created_at")

    def validate_humidityPct(self, value):
        if value < 20 or value > 100:
            raise serializers.ValidationError("湿度须在 20～100 之间")
        return value

    def validate(self, attrs):
        # 创建与单条更新（PUT/PATCH）走同一套上限判定：
        # 按采样时刻的东八区自然日找该分区上限账，湿度严格大于上限则拒绝。
        zone = attrs.get("zone", getattr(self.instance, "zone", None))
        recorded_at = attrs.get(
            "recorded_at", getattr(self.instance, "recorded_at", None)
        )
        humidity = attrs.get(
            "humidity_pct", getattr(self.instance, "humidity_pct", None)
        )
        if zone and recorded_at is not None and humidity is not None:
            cap = (
                HumidityCap.objects.filter(
                    zone=zone, work_date=east8_date(recorded_at)
                )
                .order_by("id")
                .first()
            )
            if cap is not None and humidity > cap.cap_pct:
                raise serializers.ValidationError(
                    {
                        "humidityPct": (
                            f"湿度 {humidity}% 超过该分区 "
                            f"{cap.work_date:%Y-%m-%d}（东八区）的湿度上限 "
                            f"{cap.cap_pct}%（上限账 #{cap.id}）"
                        )
                    }
                )
        return attrs


class HumidityCapSerializer(serializers.ModelSerializer):
    zoneId = serializers.PrimaryKeyRelatedField(
        source="zone", queryset=Zone.objects.all()
    )
    workDate = serializers.DateField(source="work_date")
    capPct = serializers.IntegerField(source="cap_pct")
    setBy = serializers.PrimaryKeyRelatedField(source="set_by", read_only=True)
    setByName = serializers.CharField(source="set_by.username", read_only=True)
    zoneCode = serializers.CharField(source="zone.zone_code", read_only=True)
    greenhouseName = serializers.CharField(
        source="zone.greenhouse.name", read_only=True
    )

    class Meta:
        model = HumidityCap
        fields = (
            "id",
            "zoneId",
            "zoneCode",
            "greenhouseName",
            "workDate",
            "capPct",
            "setBy",
            "setByName",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "zoneCode",
            "greenhouseName",
            "setBy",
            "setByName",
            "created_at",
            "updated_at",
        )

    def to_internal_value(self, data):
        try:
            raw = data.get("capPct")
        except AttributeError:
            raw = None
        if isinstance(raw, float) and not raw.is_integer():
            raise serializers.ValidationError(
                {"capPct": "湿度上限须为 40～100 的整数"}
            )
        return super().to_internal_value(data)

    def validate_capPct(self, value):
        if value < 40 or value > 100:
            raise serializers.ValidationError("湿度上限须为 40～100 的整数")
        return value

    def validate(self, attrs):
        zone = attrs.get("zone", getattr(self.instance, "zone", None))
        work_date = attrs.get("work_date", getattr(self.instance, "work_date", None))
        if zone and work_date:
            qs = HumidityCap.objects.filter(zone=zone, work_date=work_date)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"workDate": "该分区该作业日已存在湿度上限账（同区同日唯一）"}
                )
        return attrs


class IrrigationCycleSerializer(serializers.ModelSerializer):
    zoneId = serializers.PrimaryKeyRelatedField(
        source="zone", queryset=Zone.objects.all()
    )
    startAt = serializers.DateTimeField(source="start_at")
    durationMin = serializers.IntegerField(source="duration_min")
    waterLiters = serializers.DecimalField(
        source="water_liters", max_digits=10, decimal_places=2
    )
    zoneCode = serializers.CharField(source="zone.zone_code", read_only=True)
    greenhouseName = serializers.CharField(
        source="zone.greenhouse.name", read_only=True
    )

    class Meta:
        model = IrrigationCycle
        fields = (
            "id",
            "zoneId",
            "zoneCode",
            "greenhouseName",
            "startAt",
            "durationMin",
            "waterLiters",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "zoneCode",
            "greenhouseName",
            "created_at",
            "updated_at",
        )
