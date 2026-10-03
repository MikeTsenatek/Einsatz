from rest_framework import serializers

from .models import DischargeDestination, TreatmentKeyword, HiOrg


class TreatmentKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentKeyword
        fields = ("id", "name")
        read_only_fields = fields


class DischargeDestinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DischargeDestination
        fields = ("id", "name")
        read_only_fields = fields


class HiOrgSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = HiOrg
        fields = ("id", "hiorg", "kreisverband", "gemeinschaft", "gliederung", "label")
        read_only_fields = fields
