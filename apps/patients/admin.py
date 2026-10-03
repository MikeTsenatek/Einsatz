from django.contrib import admin
from django.forms.models import BaseInlineFormSet

from .models import Patient, Treatment


class TreatmentInlineFormSet(BaseInlineFormSet):
    def _save_with_patient_mission(self, form, treatment, commit):
        treatment.mission = self.instance.mission
        if commit:
            treatment.save()
            form.save_m2m()
        return treatment

    def save_new(self, form, commit=True):
        treatment = super().save_new(form, commit=False)
        return self._save_with_patient_mission(form, treatment, commit)

    def save_existing(self, form, obj, commit=True):
        treatment = super().save_existing(form, obj, commit=False)
        return self._save_with_patient_mission(form, treatment, commit)


class TreatmentInline(admin.StackedInline):
    model = Treatment
    readonly_fields = ("number",)
    formset = TreatmentInlineFormSet
    extra = 0
    exclude = ("mission",)
    autocomplete_fields = (
        "treater_id",
        "doctor_id",
        "assigning_enum",
        "leaving_enum",
    )
    ordering = ("-start_date",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    readonly_fields = ("number",)

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (("mission",) if obj else ())

    list_display = ("number", "name", "mission", "birthday", "age", "gender", "city")
    list_filter = ("mission", "gender", "country")
    search_fields = ("name", "street", "zip_code", "city", "country")
    autocomplete_fields = ("mission", "gender")
    list_select_related = ("mission", "gender")
    ordering = ("name",)
    inlines = (TreatmentInline,)
