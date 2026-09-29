from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.missions.models import Mission

from .models import Helper, HelperMission, Team


class HelperMissionApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="team-user")
        self.user.groups.clear()
        self.client.force_authenticate(self.user)
        self.mission = Mission.objects.create(name="Testmission")
        self.other_mission = Mission.objects.create(name="Andere Mission")

    def grant(self, *codenames):
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="teams", codename__in=codenames,
        ))
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

    def payload(self, **overrides):
        payload = {
            "helper_details": {"name": "Erika Muster", "birthday": "1990-05-10"},
            "start_date": "2026-08-25T08:00:00Z",
            "end_date": None,
        }
        payload.update(overrides)
        return payload

    def test_registers_helper_in_current_mission(self):
        self.grant("add_helper", "add_helpermission")
        response = self.client.post(
            reverse("mission-helper-list", args=(self.mission.pk,)),
            self.payload(), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["mission"], self.mission.pk)
        self.assertEqual(response.data["helper"]["name"], "Erika Muster")
        self.assertIsNone(response.data["end_date"])

    def test_list_is_limited_to_mission(self):
        helper = Helper.objects.create(name="Max Muster")
        HelperMission.objects.create(
            helper=helper, mission=self.other_mission,
            start_date=datetime(2026, 8, 25, 8, tzinfo=timezone.utc),
        )
        self.grant("view_helpermission")
        response = self.client.get(reverse("mission-helper-list", args=(self.mission.pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_rejects_end_before_start(self):
        self.grant("add_helper", "add_helpermission")
        response = self.client.post(
            reverse("mission-helper-list", args=(self.mission.pk,)),
            self.payload(end_date="2026-08-25T07:59:00Z"), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", response.data)

    def test_helper_can_be_taken_off_duty(self):
        helper = Helper.objects.create(name="Max Muster")
        assignment = HelperMission.objects.create(
            helper=helper, mission=self.mission,
            start_date=datetime(2026, 8, 25, 8, tzinfo=timezone.utc),
        )
        self.grant("change_helpermission")
        response = self.client.patch(
            reverse("mission-helper-detail", args=(self.mission.pk, assignment.pk)),
            {"end_date": "2026-08-25T16:00:00Z"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assignment.refresh_from_db()
        self.assertIsNotNone(assignment.end_date)

    def test_rejects_second_active_duty_for_same_helper(self):
        helper = Helper.objects.create(name="Max Muster")
        HelperMission.objects.create(
            helper=helper, mission=self.mission,
            start_date=datetime(2026, 8, 25, 8, tzinfo=timezone.utc),
        )
        self.grant("add_helpermission")
        response = self.client.post(
            reverse("mission-helper-list", args=(self.mission.pk,)),
            {"helper_id": helper.pk, "start_date": "2026-08-25T09:00:00Z"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    def test_helper_can_optionally_be_assigned_to_team(self):
        team = Team.objects.create(mission=self.mission, name="Sanität 1")
        self.grant("add_helper", "add_helpermission")
        response = self.client.post(
            reverse("mission-helper-list", args=(self.mission.pk,)),
            self.payload(team_id=team.pk), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["team"]["id"], team.pk)

    def test_rejects_team_from_other_mission(self):
        team = Team.objects.create(mission=self.other_mission, name="Fremdteam")
        self.grant("add_helper", "add_helpermission")
        response = self.client.post(
            reverse("mission-helper-list", args=(self.mission.pk,)),
            self.payload(team_id=team.pk), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("team_id", response.data)

    def test_creates_team_for_current_mission(self):
        self.grant("add_team")
        response = self.client.post(
            reverse("mission-team-list", args=(self.mission.pk,)),
            {"name": "Betreuung"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["mission"], self.mission.pk)
    def test_deleting_team_keeps_helper_assignment(self):
        team = Team.objects.create(mission=self.mission, name="Sanität")
        helper = Helper.objects.create(name="Max Muster")
        assignment = HelperMission.objects.create(
            helper=helper, mission=self.mission, team=team,
            start_date=datetime(2026, 8, 25, 8, tzinfo=timezone.utc),
        )
        self.grant("delete_team")
        response = self.client.delete(
            reverse("mission-team-detail", args=(self.mission.pk, team.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        assignment.refresh_from_db()
        self.assertIsNone(assignment.team)

    def test_sets_planned_end_for_helper(self):
        self.grant("add_helper", "add_helpermission")
        response = self.client.post(
            reverse("mission-helper-list", args=(self.mission.pk,)),
            self.payload(planned_end_date="2026-08-25T16:00:00Z"), format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["planned_end_date"])

    def test_sets_planned_end_for_team(self):
        team = Team.objects.create(mission=self.mission, name="Betreuung")
        self.grant("change_team")
        response = self.client.patch(
            reverse("mission-team-detail", args=(self.mission.pk, team.pk)),
            {"planned_end_date": "2026-08-25T18:00:00Z"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["planned_end_date"])

    def test_team_name_and_notes_can_be_edited_and_cleared(self):
        team = Team.objects.create(mission=self.mission, name="Betreuung")
        self.grant("change_team", "view_team")
        url = reverse("mission-team-detail", args=(self.mission.pk, team.pk))
        response = self.client.patch(url, {
            "name": "Sanität 2", "notes": "Funkrufname: San 2\nMaterial im Fahrzeug",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        team.refresh_from_db()
        self.assertEqual(team.name, "Sanität 2")
        self.assertEqual(team.notes, "Funkrufname: San 2\nMaterial im Fahrzeug")
        self.assertEqual(self.client.get(url).data["notes"], team.notes)
        response = self.client.patch(url, {"notes": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        team.refresh_from_db()
        self.assertEqual(team.notes, "")
        self.assertEqual(team.name, "Sanität 2")

    def test_team_notes_require_change_permission(self):
        team = Team.objects.create(mission=self.mission, name="Betreuung")
        self.grant("view_team")
        response = self.client.patch(
            reverse("mission-team-detail", args=(self.mission.pk, team.pk)),
            {"notes": "Nicht erlaubt"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        team.refresh_from_db()
        self.assertEqual(team.notes, "")

    def test_team_edit_is_limited_to_mission(self):
        team = Team.objects.create(mission=self.other_mission, name="Fremdteam")
        self.grant("change_team")
        response = self.client.patch(
            reverse("mission-team-detail", args=(self.mission.pk, team.pk)),
            {"notes": "Falscher Einsatz"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        team.refresh_from_db()
        self.assertEqual(team.notes, "")

    def test_duplicate_team_name_does_not_save_notes(self):
        Team.objects.create(mission=self.mission, name="Sanität")
        team = Team.objects.create(mission=self.mission, name="Betreuung", notes="Original")
        self.grant("change_team")
        response = self.client.patch(
            reverse("mission-team-detail", args=(self.mission.pk, team.pk)),
            {"name": "sanität", "notes": "Geändert"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        team.refresh_from_db()
        self.assertEqual(team.name, "Betreuung")
        self.assertEqual(team.notes, "Original")

    def test_team_end_duty_archives_and_ends_only_active_members(self):
        team = Team.objects.create(mission=self.mission, name="Sanität", notes="Bleibt erhalten")
        other_team = Team.objects.create(mission=self.mission, name="Betreuung")
        start = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)
        previous_end = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
        active = HelperMission.objects.create(helper=Helper.objects.create(name="Aktiv"), mission=self.mission, team=team, start_date=start)
        ended = HelperMission.objects.create(helper=Helper.objects.create(name="Beendet"), mission=self.mission, team=team, start_date=start, end_date=previous_end)
        other = HelperMission.objects.create(helper=Helper.objects.create(name="Andere"), mission=self.mission, team=other_team, start_date=start)
        self.grant("change_team", "change_helpermission")
        url = reverse("mission-team-end-duty", args=(self.mission.pk, team.pk))
        response = self.client.patch(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        team.refresh_from_db()
        active.refresh_from_db()
        ended.refresh_from_db()
        other.refresh_from_db()
        self.assertIsNotNone(team.end_date)
        self.assertEqual(active.end_date, team.end_date)
        self.assertEqual(ended.end_date, previous_end)
        self.assertIsNone(other.end_date)
        self.assertEqual(team.notes, "Bleibt erhalten")
        first_end = team.end_date
        self.assertEqual(self.client.patch(url, {}, format="json").status_code, status.HTTP_200_OK)
        team.refresh_from_db()
        self.assertEqual(team.end_date, first_end)

    def test_team_end_requires_permission_for_member_duties(self):
        team = Team.objects.create(mission=self.mission, name="Sanität")
        self.grant("change_team")
        response = self.client.patch(reverse("mission-team-end-duty", args=(self.mission.pk, team.pk)), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        team.refresh_from_db()
        self.assertIsNone(team.end_date)

    def test_archived_team_rejects_new_member(self):
        team = Team.objects.create(mission=self.mission, name="Archiv", end_date=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.grant("add_helper", "add_helpermission")
        response = self.client.post(reverse("mission-helper-list", args=(self.mission.pk,)), self.payload(team_id=team.pk), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(HelperMission.objects.exists())

    def test_helper_cannot_join_another_team_in_another_mission_at_same_time(self):
        helper = Helper.objects.create(name="Max")
        first = Team.objects.create(mission=self.other_mission, name="Erstes Team")
        second = Team.objects.create(mission=self.mission, name="Zweites Team")
        HelperMission.objects.create(helper=helper, mission=self.other_mission, team=first, start_date=datetime(2026, 8, 25, 8, tzinfo=timezone.utc))
        self.grant("add_helpermission")
        response = self.client.post(reverse("mission-helper-list", args=(self.mission.pk,)), {"helper_id": helper.pk, "team_id": second.pk, "start_date": "2026-08-25T09:00:00Z"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("team_id", response.data)

    def test_consecutive_team_duties_allowed_but_historical_overlap_rejected(self):
        helper = Helper.objects.create(name="Max")
        first = Team.objects.create(mission=self.mission, name="Erstes Team")
        second = Team.objects.create(mission=self.mission, name="Zweites Team")
        HelperMission.objects.create(helper=helper, mission=self.mission, team=first, start_date=datetime(2026, 8, 25, 8, tzinfo=timezone.utc), end_date=datetime(2026, 8, 25, 10, tzinfo=timezone.utc))
        self.grant("add_helpermission")
        url = reverse("mission-helper-list", args=(self.mission.pk,))
        payload = {"helper_id": helper.pk, "team_id": second.pk, "start_date": "2026-08-25T09:00:00Z", "end_date": "2026-08-25T11:00:00Z"}
        self.assertEqual(self.client.post(url, payload, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        payload["start_date"] = "2026-08-25T10:00:00Z"
        self.assertEqual(self.client.post(url, payload, format="json").status_code, status.HTTP_201_CREATED)

    def test_search_finds_helpers_from_previous_missions_once(self):
        helper = Helper.objects.create(name="Erika Muster", birthday="1990-05-10")
        for hour in (8, 10):
            HelperMission.objects.create(
                helper=helper, mission=self.other_mission,
                start_date=datetime(2026, 1, 1, hour, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 1, hour + 1, tzinfo=timezone.utc),
            )
        Helper.objects.create(name="Andere Person")
        self.grant("view_helper")
        response = self.client.get(reverse("helper-search"), {"name": "  Muster  "})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0], {"id": helper.pk, "name": "Erika Muster", "birthday": "1990-05-10"})

    def test_search_requires_permission_and_minimum_query(self):
        Helper.objects.create(name="Erika Muster")
        url = reverse("helper-search")
        self.assertEqual(self.client.get(url, {"name": "Erika"}).status_code, status.HTTP_403_FORBIDDEN)
        self.grant("view_helper")
        for name in ("", "E", "unbekannt"):
            self.assertEqual(self.client.get(url, {"name": name}).data, [])

    def test_search_limits_results_and_keeps_same_name_people_distinct(self):
        for index in range(25):
            Helper.objects.create(name="Erika Muster", birthday=f"1990-01-{index + 1:02d}")
        self.grant("view_helper")
        response = self.client.get(reverse("helper-search"), {"name": "Erika"})
        self.assertEqual(len(response.data), 20)
        self.assertEqual(len({item["id"] for item in response.data}), 20)

    def test_selected_previous_helper_is_reused_without_changing_old_duty(self):
        helper = Helper.objects.create(name="Erika Muster", birthday="1990-05-10")
        old = HelperMission.objects.create(
            helper=helper, mission=self.other_mission,
            start_date=datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 1, 9, tzinfo=timezone.utc),
        )
        self.grant("add_helpermission")
        response = self.client.post(
            reverse("mission-helper-list", args=(self.mission.pk,)),
            {"helper_id": helper.pk, "start_date": "2026-08-25T08:00:00Z"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["helper"]["id"], helper.pk)
        self.assertEqual(Helper.objects.count(), 1)
        old.refresh_from_db()
        self.assertIsNotNone(old.end_date)

    def test_deleting_helper_removes_all_duties_but_keeps_teams_and_treatments(self):
        from apps.patients.models import Treatment
        helper = Helper.objects.create(name="Zu löschen")
        other = Helper.objects.create(name="Bleibt")
        team = Team.objects.create(mission=self.mission, name="Bleibt ebenfalls")
        start = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)
        for mission in (self.mission, self.other_mission):
            HelperMission.objects.create(helper=helper, mission=mission, start_date=start)
        treatment = Treatment.objects.create(mission=self.mission, start_date=start, treater_id=helper, doctor_id=helper)
        self.grant("delete_helper", "delete_helpermission", "view_helper")
        response = self.client.delete(reverse("helper-delete", args=(helper.pk,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Helper.objects.filter(pk=helper.pk).exists())
        self.assertFalse(HelperMission.objects.filter(helper_id=helper.pk).exists())
        self.assertTrue(Helper.objects.filter(pk=other.pk).exists())
        self.assertTrue(Team.objects.filter(pk=team.pk).exists())
        treatment.refresh_from_db()
        self.assertIsNone(treatment.treater_id)
        self.assertIsNone(treatment.doctor_id)
        self.assertEqual(self.client.get(reverse("helper-search"), {"name": "Zu löschen"}).data, [])

    def test_deleting_helper_requires_both_delete_permissions(self):
        helper = Helper.objects.create(name="Geschützt")
        url = reverse("helper-delete", args=(helper.pk,))
        self.grant("delete_helpermission")
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)
        self.user.user_permissions.clear()
        self.grant("delete_helper")
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Helper.objects.filter(pk=helper.pk).exists())

    def test_deleting_missing_helper_returns_not_found(self):
        self.grant("delete_helper", "delete_helpermission")
        self.assertEqual(self.client.delete(reverse("helper-delete", args=(999999,))).status_code, status.HTTP_404_NOT_FOUND)
