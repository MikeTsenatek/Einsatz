from django.contrib import admin

from .models import AssigningEnum, GenderEnum, LeavingEnum, PriorityEnum, TreatmentKeyword


@admin.register(AssigningEnum)
@admin.register(GenderEnum)
class NamedReferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("id",)


@admin.register(LeavingEnum)
class LeavingEnumAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "has_to_be_specified")
    list_filter = ("has_to_be_specified",)
    search_fields = ("name",)
    ordering = ("id",)


@admin.register(PriorityEnum)
class PriorityEnumAdmin(admin.ModelAdmin):
    list_display = ("level", "name")
    search_fields = ("name",)
    ordering = ("level",)



@admin.register(TreatmentKeyword)
class TreatmentKeywordAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_editable = ("is_active",)
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)
