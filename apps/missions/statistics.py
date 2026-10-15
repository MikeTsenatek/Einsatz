"""Daily counts for a mission, using local calendar days."""
from collections import defaultdict
from datetime import timedelta

from apps.patients.models import calculate_age

from django.utils import timezone


def daily_statistics(mission, user):
    permissions = {
        "entries": user.has_perm("missions.view_operationlogentry"),
        "treatments": user.has_perm("patients.view_treatment"),
        "transports": user.has_perm("patients.view_treatment"),
        "helpers": user.has_perm("teams.view_helpermission"),
        "teams": user.has_perms(("teams.view_helpermission", "teams.view_team")),
    }
    now = timezone.now()
    treatment_intervals = defaultdict(list)
    helper_intervals = defaultdict(list)
    treatment_seconds = 0
    transport_hours = defaultdict(int)
    counts = defaultdict(lambda: {key: set() for key in permissions})

    def add(timestamp, key, identity):
        counts[timezone.localdate(timestamp)][key].add(identity)

    if permissions["entries"]:
        for timestamp, pk in mission.operation_log_entries.filter(is_struck_out=False).values_list("timestamp", "pk"):
            add(timestamp, "entries", pk)
    if permissions["treatments"] or permissions["transports"]:
        for treatment in mission.treatments.values("pk", "start_date", "end_date", "transported_by_public_ems", "patient_id"):
            start, end = treatment["start_date"], min(treatment["end_date"] or now, now)
            if end > start:
                treatment_seconds += (end - start).total_seconds()
                identity = ("patient", treatment.get("patient_id")) if treatment.get("patient_id") else ("treatment", treatment["pk"])
                treatment_intervals[identity].append((start, end))
            if permissions["treatments"]:
                add(treatment["start_date"], "treatments", treatment["pk"])
            if permissions["transports"] and treatment["transported_by_public_ems"] and treatment["end_date"]:
                add(treatment["end_date"], "transports", treatment["pk"])
                transport_hour = treatment["end_date"].replace(minute=0, second=0, microsecond=0)
                transport_hours[transport_hour] += 1
    if permissions["helpers"]:
        for assignment in mission.helpermission_set.select_related("team"):
            end = assignment.end_date
            if assignment.team and assignment.team.end_date:
                end = min(end, assignment.team.end_date) if end else assignment.team.end_date
            effective_end = min(end or now, now)
            if effective_end > assignment.start_date:
                helper_intervals[assignment.helper_id].append((assignment.start_date, effective_end))
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
    def merged(intervals):
        result = []
        for start, end in sorted(intervals):
            if result and start <= result[-1][1]:
                result[-1] = (result[-1][0], max(end, result[-1][1]))
            else:
                result.append((start, end))
        return result

    hours = defaultdict(float)
    for intervals in treatment_intervals.values():
        for start, end in merged(intervals):
            hour = start.replace(minute=0, second=0, microsecond=0)
            while hour < end:
                following = hour + timedelta(hours=1)
                hours[hour] += (min(end, following) - max(start, hour)).total_seconds() / 3600
                hour = following
    hourly = []
    chart_hours = hours.keys() | transport_hours.keys()
    if chart_hours:
        hour, last = min(chart_hours), max(chart_hours)
        while hour <= last:
            hourly.append({"start": hour.isoformat(), "date": timezone.localdate(hour).isoformat(), "patients": round(hours[hour], 3), "transports": transport_hours[hour] if permissions["transports"] else None})
            hour += timedelta(hours=1)
    ages = []
    can_view_age = user.has_perm("patients.view_patient")
    if can_view_age:
        for patient in mission.patients.values("birthday", "age"):
            age = calculate_age(patient["birthday"]) if patient["birthday"] else patient["age"]
            if age is not None and age >= 0:
                ages.append(age)
    return {
        "days": rows, "available": permissions, "timezone": str(timezone.get_current_timezone()),
        "summary": {
            "treatment_seconds": treatment_seconds if permissions["treatments"] else None,
            "helper_seconds": sum((end - start).total_seconds() for intervals in helper_intervals.values() for start, end in merged(intervals)) if permissions["helpers"] else None,
            "average_age": sum(ages) / len(ages) if ages else None,
            "known_age_count": len(ages) if can_view_age else None,
        },
        "hourly": hourly if permissions["treatments"] else None,
    }
