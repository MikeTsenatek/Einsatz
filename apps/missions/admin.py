from auditlog.mixins import AuditlogHistoryAdminMixin
from django.contrib import admin

from .models import OperationLogEntry, Mission


@admin.register(Mission)
class MissionAdmin(AuditlogHistoryAdminMixin, admin.ModelAdmin):
    list_display = ("id", "name", "state")
    list_filter = ("state",)
    search_fields = ("name",)
    ordering = ("name",)
    show_auditlog_history_link = True


@admin.register(OperationLogEntry)
class OperationLogEntryAdmin(AuditlogHistoryAdminMixin, admin.ModelAdmin):
    readonly_fields = ("number",)

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (("mission",) if obj else ())

    list_display = (
        "number",
        "mission",
        "timestamp",
        "sender",
        "recipient",
        "priority",
        "is_struck_out",
    )
    list_filter = ("is_struck_out", "mission", "priority", "timestamp")
    search_fields = ("sender", "recipient", "text", "measure", "mission__name")
    autocomplete_fields = ("mission", "priority")
    list_select_related = ("mission", "priority")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
    show_auditlog_history_link = True

    def has_delete_permission(self, request, obj=None):
        return False
