from rest_framework import serializers

from .models import DischargeDestination, TreatmentKeyword


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
