from django.contrib import admin

from .models import Helper, HelperMission, Team


@admin.register(Helper)
class HelperAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "birthday", "city", "country")
    list_filter = ("country", "city")
    search_fields = ("name", "street", "zip_code", "city", "country")
    ordering = ("name",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "mission")
    list_filter = ("mission",)
    search_fields = ("name", "mission__name")


@admin.register(HelperMission)
class HelperMissionAdmin(admin.ModelAdmin):
    list_display = ("id", "helper", "mission", "team", "start_date", "end_date")
    list_filter = ("mission", "team", "start_date", "end_date")
    search_fields = ("helper__name", "mission__name", "team__name")
    autocomplete_fields = ("helper", "mission", "team")
    list_select_related = ("helper", "mission", "team")
    date_hierarchy = "start_date"
    ordering = ("-start_date",)
