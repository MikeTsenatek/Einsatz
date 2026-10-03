"""Daily counts for a mission, using local calendar days."""
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone


def daily_statistics(mission, user):
    permissions = {
        "entries": user.has_perm("missions.view_operationlogentry"),
        "treatments": user.has_perm("patients.view_treatment"),
        "transports": user.has_perm("patients.view_treatment"),
        "helpers": user.has_perm("teams.view_helpermission"),
        "teams": user.has_perms(("teams.view_helpermission", "teams.view_team")),
    }
    counts = defaultdict(lambda: {key: set() for key in permissions})

    def add(timestamp, key, identity):
        counts[timezone.localdate(timestamp)][key].add(identity)

    if permissions["entries"]:
        for timestamp, pk in mission.operation_log_entries.filter(is_struck_out=False).values_list("timestamp", "pk"):
            add(timestamp, "entries", pk)
    if permissions["treatments"] or permissions["transports"]:
        for treatment in mission.treatments.values("pk", "start_date", "end_date", "transported_by_public_ems"):
            if permissions["treatments"]:
                add(treatment["start_date"], "treatments", treatment["pk"])
            if permissions["transports"] and treatment["transported_by_public_ems"] and treatment["end_date"]:
                add(treatment["end_date"], "transports", treatment["pk"])
    if permissions["helpers"]:
        for assignment in mission.helpermission_set.select_related("team"):
            end = assignment.end_date
            if assignment.team and assignment.team.end_date:
                end = min(end, assignment.team.end_date) if end else assignment.team.end_date
            day = timezone.localdate(assignment.start_date)
            # Ongoing attendance is counted up to today, never on future days.
            last = timezone.localdate(end) if end else timezone.localdate()
            while day <= last:
                counts[day]["helpers"].add(assignment.helper_id)
                if permissions["teams"] and assignment.team_id:
                    counts[day]["teams"].add(assignment.team_id)
                day += timedelta(days=1)
    rows = []
    if counts:
        day, last = min(counts), max(counts)
        while day <= last:
            rows.append({
                "date": day.isoformat(),
                **{key: len(counts[day][key]) if allowed else None for key, allowed in permissions.items()},
            })
            day += timedelta(days=1)
    return {"days": rows, "available": permissions, "timezone": str(timezone.get_current_timezone())}
