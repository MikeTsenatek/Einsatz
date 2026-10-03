from datetime import datetime, timezone as utc_timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Mission
from .statistics import daily_statistics


def timestamp(day, hour=12):
    return datetime(2020, 5, day, hour, tzinfo=utc_timezone.utc)


class DailyStatisticsTests(SimpleTestCase):
    def setUp(self):
        self.user = Mock()
        self.user.has_perm.return_value = True
        self.user.has_perms.return_value = True
        self.mission = Mock()
        self.mission.operation_log_entries.filter.return_value.values_list.return_value = []
        self.mission.treatments.values.return_value = []
        self.mission.helpermission_set.select_related.return_value = []

    def test_each_treatment_counts_on_start_day_and_transport_on_completion_day(self):
        self.mission.treatments.values.return_value = [
            {"pk": 1, "patient_id": 7, "start_date": timestamp(1), "end_date": timestamp(2), "transported_by_public_ems": True},
            {"pk": 2, "patient_id": 7, "start_date": timestamp(1), "end_date": None, "transported_by_public_ems": True},
            {"pk": 3, "patient_id": None, "start_date": timestamp(1), "end_date": None, "transported_by_public_ems": False},
            {"pk": 4, "patient_id": 7, "start_date": timestamp(3), "end_date": timestamp(3), "transported_by_public_ems": False},
        ]
        days = daily_statistics(self.mission, self.user)["days"]
        self.assertEqual([day["treatments"] for day in days], [3, 0, 1])
        self.assertEqual([day["transports"] for day in days], [0, 1, 0])

    def test_treatment_count_only_requires_treatment_view_permission(self):
        self.user.has_perm.side_effect = lambda permission: permission == "patients.view_treatment"
        self.user.has_perms.return_value = False
        self.mission.treatments.values.return_value = [
            {"pk": 1, "start_date": timestamp(1, 23), "end_date": None, "transported_by_public_ems": False},
        ]
        data = daily_statistics(self.mission, self.user)
        self.assertTrue(data["available"]["treatments"])
        self.assertEqual(data["days"][0]["date"], "2020-05-02")
        self.assertEqual(data["days"][0]["treatments"], 1)

    def test_helpers_and_teams_are_unique_and_count_each_attendance_day(self):
        team = SimpleNamespace(end_date=None)
        self.mission.helpermission_set.select_related.return_value = [
            SimpleNamespace(helper_id=1, team_id=10, team=team, start_date=timestamp(1), end_date=timestamp(3)),
            SimpleNamespace(helper_id=1, team_id=10, team=team, start_date=timestamp(2), end_date=timestamp(2)),
            SimpleNamespace(helper_id=2, team_id=10, team=team, start_date=timestamp(2), end_date=timestamp(2)),
            SimpleNamespace(helper_id=3, team_id=None, team=None, start_date=timestamp(3), end_date=None),
        ]
        with patch("apps.missions.statistics.timezone.localdate", side_effect=lambda value=None: value.astimezone(ZoneInfo('Europe/Berlin')).date() if value else timestamp(4).date()):
            days = daily_statistics(self.mission, self.user)["days"]
        self.assertEqual([day["helpers"] for day in days], [1, 2, 2, 1])
        self.assertEqual([day["teams"] for day in days], [1, 1, 1, 0])

    def test_etb_uses_local_day_and_omits_struck_entries(self):
        self.mission.operation_log_entries.filter.return_value.values_list.return_value = [(timestamp(1, 23), 1)]
        result = daily_statistics(self.mission, self.user)
        self.assertEqual(result["days"][0]["date"], "2020-05-02")
        self.assertEqual(result["days"][0]["entries"], 1)
        self.mission.operation_log_entries.filter.assert_called_once_with(is_struck_out=False)

    def test_missing_permissions_do_not_query_sources(self):
        self.user.has_perm.return_value = False
        self.user.has_perms.return_value = False
        self.assertEqual(daily_statistics(self.mission, self.user)["days"], [])
        self.mission.operation_log_entries.filter.assert_not_called()
        self.mission.treatments.values.assert_not_called()
        self.mission.helpermission_set.select_related.assert_not_called()

    def test_unavailable_columns_are_null_and_empty_days_are_included(self):
        self.user.has_perm.side_effect = lambda permission: permission == "missions.view_operationlogentry"
        self.user.has_perms.return_value = False
        self.mission.operation_log_entries.filter.return_value.values_list.return_value = [(timestamp(1), 1), (timestamp(3), 2)]
        days = daily_statistics(self.mission, self.user)["days"]
        self.assertEqual([day["entries"] for day in days], [1, 0, 1])
        self.assertTrue(all(day["treatments"] is None for day in days))


class StatisticsApiTests(APITestCase):
    def test_requires_mission_permission_and_isolates_mission(self):
        user = get_user_model().objects.create_user(username="statistics")
        user.groups.clear()
        mission = Mission.objects.create(name="Statistik")
        url = reverse("mission-statistics", args=(mission.pk,))
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(url).status_code, 403)
        user.user_permissions.add(Permission.objects.get(content_type__app_label="missions", codename="view_mission"))
        user = get_user_model().objects.get(pk=user.pk)
        self.client.force_authenticate(user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["days"], [])
        self.assertFalse(any(response.data["available"].values()))
        self.assertEqual(self.client.get(reverse("mission-statistics", args=(mission.pk + 100,))).status_code, 404)
