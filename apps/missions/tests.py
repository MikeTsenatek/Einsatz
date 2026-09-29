from datetime import datetime, timezone

from auditlog.context import set_actor
from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.mgmt.models import PriorityEnum

from .models import OperationLogEntry, Mission


class MissionApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dispatcher",
            password="secure-password",
        )
        self.client.force_authenticate(self.user)
        self.mission = Mission.objects.create(name="Testmission")

    def grant(self, codename):
        permission = Permission.objects.get(
            content_type__app_label="missions",
            codename=codename,
        )
        self.user.user_permissions.add(permission)
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

    def test_read_requires_authentication_but_no_model_permission(self):
        list_url = reverse("mission-list")
        detail_url = reverse("mission-detail", args=(self.mission.pk,))

        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(list_url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(list_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)

    def test_write_actions_require_standard_model_permissions(self):
        list_url = reverse("mission-list")
        detail_url = reverse("mission-detail", args=(self.mission.pk,))

        self.assertEqual(
            self.client.post(list_url, {"name": "Neue Mission"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("add_mission")
        self.assertEqual(
            self.client.post(list_url, {"name": "Neue Mission"}).status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            self.client.patch(detail_url, {"state": Mission.State.INACTIVE}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("change_mission")
        self.assertEqual(
            self.client.patch(detail_url, {"state": Mission.State.INACTIVE}).status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.grant("delete_mission")
        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )


class OperationLogEntryTests(TestCase):
    def test_delete_permission_does_not_exist(self):
        self.assertFalse(
            Permission.objects.filter(
                content_type__app_label="missions",
                codename="delete_operationlogentry",
            ).exists()
        )

    def setUp(self):
        self.mission = Mission.objects.create(name="Auditmission")
        self.priority = PriorityEnum.objects.create(level=1, name="Sehr hoch")

    def create_entry(self):
        return OperationLogEntry.objects.create(
            mission=self.mission,
            sender="Einsatzleitung",
            recipient="San-Team",
            timestamp=datetime(2026, 8, 22, 12, 30, tzinfo=timezone.utc),
            text="Patient gemeldet",
            measure="Team entsandt",
            priority=self.priority,
        )

    def test_struck_out_entry_remains_visible_and_is_audited(self):
        user = get_user_model().objects.create_user(username="auditor")

        with set_actor(user):
            entry = self.create_entry()
            entry.text = "Patient übernommen"
            entry.save()
            entry.is_struck_out = True
            entry.save()

        persisted_entry = OperationLogEntry.objects.get(pk=entry.pk)
        self.assertTrue(persisted_entry.is_struck_out)

        logs = LogEntry.objects.filter(
            content_type__app_label="missions",
            content_type__model="operationlogentry",
            object_pk=str(entry.pk),
        ).order_by("timestamp")

        self.assertEqual(logs.count(), 3)
        self.assertEqual(
            set(logs.values_list("action", flat=True)),
            {LogEntry.Action.CREATE, LogEntry.Action.UPDATE},
        )
        self.assertTrue(all(log.actor_id == user.pk for log in logs))
        self.assertTrue(all(log.serialized_data is not None for log in logs))

    def test_entry_cannot_be_deleted_directly_or_in_bulk(self):
        entry = self.create_entry()

        with self.assertRaises(DjangoValidationError):
            entry.delete()
        with self.assertRaises(DjangoValidationError):
            OperationLogEntry.objects.filter(pk=entry.pk).delete()
        with self.assertRaises(DjangoValidationError):
            OperationLogEntry.objects.filter(pk=entry.pk).update(is_struck_out=True)

        self.assertTrue(OperationLogEntry.objects.filter(pk=entry.pk).exists())

    def test_mission_with_operation_log_entry_cannot_be_deleted(self):
        self.create_entry()

        with self.assertRaises(ProtectedError):
            self.mission.delete()

        self.assertTrue(Mission.objects.filter(pk=self.mission.pk).exists())


class OperationLogEntryApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operation-log-user",
            password="secure-password",
        )
        self.client.force_authenticate(self.user)
        self.mission = Mission.objects.create(name="OperationLogEntry Mission")
        self.other_mission = Mission.objects.create(name="Andere Mission")
        self.priority = PriorityEnum.objects.create(level=3, name="Normal")

    def grant(self, codename):
        permission = Permission.objects.get(
            content_type__app_label="missions",
            codename=codename,
        )
        self.user.user_permissions.add(permission)
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

    def payload(self):
        return {
            "sender": "Einsatzleitung",
            "recipient": "San-Team 1",
            "timestamp": "2026-08-22T12:30:00Z",
            "text": "Patient im Nordbereich gemeldet",
            "measure": "San-Team entsandt",
            "priority": self.priority.pk,
        }

    def test_list_is_limited_to_requested_mission(self):
        OperationLogEntry.objects.create(
            mission=self.other_mission,
            sender="Andere",
            recipient="Andere",
            timestamp=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
            text="Nicht sichtbar",
            measure="Keine",
            priority=self.priority,
        )

        response = self.client.get(reverse("operation-log-entry-list", args=(self.mission.pk,)))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_create_requires_add_permission_and_uses_url_mission(self):
        url = reverse("operation-log-entry-list", args=(self.mission.pk,))

        self.assertEqual(self.client.post(url, self.payload()).status_code, status.HTTP_403_FORBIDDEN)

        self.grant("add_operationlogentry")
        response = self.client.post(url, self.payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["mission"], self.mission.pk)
        self.assertEqual(response.data["priority_level"], 3)

    def test_patch_allows_audited_edits_and_striking(self):
        entry = OperationLogEntry.objects.create(
            mission=self.mission,
            sender="Einsatzleitung",
            recipient="San-Team",
            timestamp=datetime(2026, 8, 22, 12, 30, tzinfo=timezone.utc),
            text="Meldung",
            measure="Maßnahme",
            priority=self.priority,
        )
        self.grant("change_operationlogentry")
        url = reverse("operation-log-entry-detail", args=(self.mission.pk, entry.pk))

        with set_actor(self.user):
            edited = self.client.patch(url, {"text": "Korrigierte Meldung"}, format="json")
        self.assertEqual(edited.status_code, status.HTTP_200_OK)
        self.assertEqual(edited.data["text"], "Korrigierte Meldung")

        history = self.client.get(
            reverse("operation-log-entry-history", args=(self.mission.pk, entry.pk))
        )
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        text_changes = [
            event["changes"]["text"]
            for event in history.data
            if "text" in event["changes"]
        ]
        self.assertIn(["Meldung", "Korrigierte Meldung"], text_changes)

        response = self.client.patch(url, {"is_struck_out": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_struck_out"])
        rejected = self.client.patch(url, {"text": "Zu spät"}, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

        listed = self.client.get(reverse("operation-log-entry-list", args=(self.mission.pk,)))
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(len(listed.data["results"]), 1)
        self.assertTrue(listed.data["results"][0]["is_struck_out"])


class OptionalOperationLogFieldsApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="optional-fields-user")
        self.client.force_authenticate(self.user)
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="missions",
                codename="add_operationlogentry",
            )
        )
        self.mission = Mission.objects.create(name="Einsatz mit optionalen Feldern")
        self.priority = PriorityEnum.objects.create(level=4, name="Niedrig")

    def test_sender_recipient_and_measure_are_optional(self):
        response = self.client.post(
            reverse("operation-log-entry-list", args=(self.mission.pk,)),
            {
                "timestamp": "2026-08-22T12:30:00Z",
                "text": "Reine Lagemeldung",
                "priority": self.priority.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["sender"], "")
        self.assertEqual(response.data["recipient"], "")
        self.assertEqual(response.data["measure"], "")
