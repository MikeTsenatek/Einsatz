from rest_framework import serializers

from .models import Helper, HelperMission, Team


class HelperDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Helper
        fields = ("name", "birthday", "street", "zip_code", "city", "country")


class HelperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Helper
        fields = ("id", "name", "birthday", "street", "zip_code", "city", "country")
        read_only_fields = ("id",)


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ("id", "mission", "name", "notes", "planned_end_date", "end_date")
        read_only_fields = ("id", "mission", "end_date")
        validators = ()

    def validate_name(self, value):
        mission_id = getattr(self.context.get("view"), "kwargs", {}).get("mission_pk")
        teams = Team.objects.filter(mission_id=mission_id, name__iexact=value.strip())
        if self.instance is not None:
            teams = teams.exclude(pk=self.instance.pk)
        if teams.exists():
            raise serializers.ValidationError(
                "Ein Team mit diesem Namen existiert bereits."
            )
        return value.strip()


class HelperMissionSerializer(serializers.ModelSerializer):
    helper = HelperSerializer(read_only=True)
    helper_id = serializers.PrimaryKeyRelatedField(
        source="helper", queryset=Helper.objects.all(), required=False, write_only=True,
    )
    helper_details = HelperDetailsSerializer(write_only=True, required=False)
    team = TeamSerializer(read_only=True)
    team_id = serializers.PrimaryKeyRelatedField(
        source="team", queryset=Team.objects.all(), required=False,
        allow_null=True, write_only=True,
    )

    class Meta:
        model = HelperMission
        fields = (
            "id", "mission", "helper", "helper_id", "helper_details",
            "team", "team_id", "start_date", "planned_end_date", "end_date",
        )
        read_only_fields = ("id", "mission")

    def validate(self, attrs):
        helper = attrs.get("helper", getattr(self.instance, "helper", None))
        if self.instance is None and helper is None and not attrs.get("helper_details"):
            raise serializers.ValidationError({"helper_details": "Helferdaten sind erforderlich."})
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        planned_end_date = attrs.get(
            "planned_end_date", getattr(self.instance, "planned_end_date", None)
        )
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "Das Dienstende darf nicht vor dem Dienstbeginn liegen."
            })
        if start_date and planned_end_date and planned_end_date < start_date:
            raise serializers.ValidationError({
                "planned_end_date": "Das geplante Dienstende darf nicht vor dem Dienstbeginn liegen."
            })
        team = attrs.get("team", getattr(self.instance, "team", None))
        mission_id = getattr(self.context.get("view"), "kwargs", {}).get("mission_pk")
        if team is not None and str(team.mission_id) != str(mission_id):
            raise serializers.ValidationError({
                "team_id": "Das Team gehört zu einem anderen Einsatz."
            })
        return attrs


class HelperSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Helper
        fields = ("id", "name", "birthday")
        read_only_fields = fields
