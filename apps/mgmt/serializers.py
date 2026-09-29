from rest_framework import serializers

from .models import TreatmentKeyword


class TreatmentKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentKeyword
        fields = ("id", "name")
        read_only_fields = fields
