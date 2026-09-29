from rest_framework import serializers

from apps.mgmt.models import PriorityEnum

from .models import OperationLogEntry, Mission


class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = ("id", "name", "state")
        read_only_fields = ("id",)


class PrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorityEnum
        fields = ("id", "level", "name")
        read_only_fields = fields


class OperationLogEntrySerializer(serializers.ModelSerializer):
    priority_name = serializers.CharField(source="priority.name", read_only=True)
    priority_level = serializers.IntegerField(source="priority.level", read_only=True)

    class Meta:
        model = OperationLogEntry
        fields = (
            "id",
            "mission",
            "sender",
            "recipient",
            "timestamp",
            "text",
            "measure",
            "priority",
            "priority_name",
            "priority_level",
            "is_struck_out",
        )
        read_only_fields = ("id", "mission", "is_struck_out", "priority_name", "priority_level")

