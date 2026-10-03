from django.utils import timezone
from rest_framework import serializers

from .models import Patient, Treatment, calculate_age


class PatientSearchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    birthday = serializers.DateField(required=False)

    def validate(self, attrs):
        if not attrs.get("name") and not attrs.get("birthday"):
            raise serializers.ValidationError("Name oder Geburtsdatum ist erforderlich.")
        return attrs


class PatientSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source="__str__", read_only=True)
    treatment_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Patient
        fields = (
            "id", "number", "mission", "name", "display_name",
            "birthday", "age", "gender", "street", "zip_code", "city", "country",
            "treatment_count",
        )
        read_only_fields = ("id", "number", "display_name", "treatment_count")

    def validate(self, attrs):
        if self.instance and attrs.get("mission", self.instance.mission).pk != self.instance.mission_id:
            raise serializers.ValidationError({"mission": "Der Einsatz eines nummerierten Patienten darf nicht geändert werden."})
        birthday = attrs.get("birthday", getattr(self.instance, "birthday", None))
        if birthday:
            if birthday > timezone.localdate():
                raise serializers.ValidationError({"birthday": "Das Geburtsdatum darf nicht in der Zukunft liegen."})
            attrs["age"] = calculate_age(birthday)
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.birthday:
            data["age"] = calculate_age(instance.birthday)
        return data




class TreatmentPatientDetailsSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    birthday = serializers.DateField(required=False, allow_null=True)
    age = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=130)

    def validate(self, attrs):
        birthday = attrs.get("birthday")
        if birthday:
            if birthday > timezone.localdate():
                raise serializers.ValidationError({"birthday": "Das Geburtsdatum darf nicht in der Zukunft liegen."})
            attrs["age"] = calculate_age(birthday)
        return attrs


class TreatmentPatientSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Patient
        fields = ("id", "number", "name", "display_name", "birthday", "age", "gender")
        read_only_fields = ("number",)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.birthday:
            data["age"] = calculate_age(instance.birthday)
        return data


class TreatmentPatientField(serializers.PrimaryKeyRelatedField):
    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return TreatmentPatientSerializer(value, context=self.context).data


class TreatmentSerializer(serializers.ModelSerializer):
    patient = TreatmentPatientField(queryset=Patient.objects.all(), required=False, allow_null=True)
    patient_details = TreatmentPatientDetailsSerializer(write_only=True, required=False)
    create_new_patient = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = Treatment
        fields = (
            "id", "mission", "patient", "patient_details", "create_new_patient", "start_date", "end_date",
            "keyword", "notes", "treater_text", "treater_id", "doctor_text",
            "doctor_id", "assigning_enum", "leaving_enum", "leaving_specified",
            "external_order_number",
        )
        read_only_fields = ("id", "mission")

    def validate(self, attrs):
        patient = attrs.get("patient", getattr(self.instance, "patient", None))
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        keyword = attrs.get("keyword", getattr(self.instance, "keyword", None))

        nested_patient_id = getattr(self.context.get("view"), "kwargs", {}).get("patient_pk")
        patient_details = attrs.get("patient_details")
        if attrs.get("create_new_patient") and not patient_details:
            raise serializers.ValidationError({
                "patient_details": "Für einen neuen Patienten werden Patientendaten benötigt."
            })
        if end_date is not None and patient is None and not patient_details and not nested_patient_id:
            raise serializers.ValidationError({
                "end_date": "Eine Behandlung kann nur mit zugeordnetem Patienten abgeschlossen werden."
            })
        if end_date is not None and not (keyword or "").strip():
            raise serializers.ValidationError({
                "keyword": "Zum Abschließen einer Behandlung ist ein Stichwort erforderlich."
            })
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "Das Ende darf nicht vor dem Beginn liegen."
            })
        return attrs

