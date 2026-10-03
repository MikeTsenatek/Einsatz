from django.test import TestCase

from .models import AssigningEnum, GenderEnum, LeavingEnum, PriorityEnum


class ManagementFixturesTests(TestCase):
    fixtures = ("initial_data.json",)

    def test_fixture_contains_reference_data(self):
        self.assertEqual(GenderEnum.objects.count(), 3)
        self.assertEqual(AssigningEnum.objects.count(), 5)
        self.assertEqual(LeavingEnum.objects.count(), 5)
        self.assertEqual(PriorityEnum.objects.count(), 4)
        self.assertEqual(
            list(PriorityEnum.objects.values_list("level", "name")),
            [
                (1, "Sehr hoch"),
                (2, "dringend"),
                (3, "normal"),
                (4, "niedrig"),
            ],
        )

    def test_leaving_options_requiring_details(self):
        requiring_details = set(
            LeavingEnum.objects.filter(has_to_be_specified=True).values_list(
                "name", flat=True
            )
        )

        self.assertEqual(requiring_details, {"Krankenhaus", "Sonst"})


from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import TreatmentKeyword


class TreatmentKeywordTests(TestCase):
    fixtures = ("initial_data.json",)

    def test_fixture_contains_deduplicated_keyword_suggestions(self):
        self.assertEqual(TreatmentKeyword.objects.count(), 189)
        self.assertTrue(
            TreatmentKeyword.objects.filter(name="Schlaganfall").exists()
        )
        self.assertEqual(
            TreatmentKeyword.objects.filter(name="Bewusstseinsstörung").count(),
            1,
        )

    def test_keyword_is_editable_in_admin(self):
        self.assertTrue(admin.site.is_registered(TreatmentKeyword))


class TreatmentKeywordApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="keyword-user")
        self.active = TreatmentKeyword.objects.create(
            name="Aktiver Vorschlag",
        )
        TreatmentKeyword.objects.create(
            name="Inaktiver Vorschlag",
            is_active=False,
        )

    def test_list_requires_authentication_and_only_returns_active_suggestions(self):
        url = reverse("treatment-keyword-list")
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [keyword["name"] for keyword in response.data],
            ["Aktiver Vorschlag"],
        )


from django.contrib.auth.models import Permission
from .models import DischargeDestination


class DischargeDestinationTests(TestCase):
    fixtures = ("initial_data.json",)

    def test_fixture_contains_requested_suggestions(self):
        self.assertEqual(list(DischargeDestination.objects.filter(is_active=True).values_list("name", flat=True)), [
            "Zurück zur Veranstaltung", "Nach Hause", "Krankenhaus",
        ])
        self.assertTrue(admin.site.is_registered(DischargeDestination))


class DischargeDestinationApiTests(APITestCase):
    def test_suggestions_require_permission_and_hide_inactive_entries(self):
        active = DischargeDestination.objects.create(name="Nach Hause")
        DischargeDestination.objects.create(name="Inaktiv", is_active=False)
        url = reverse("discharge-destination-list")
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)
        user = get_user_model().objects.create_user(username="discharge-user")
        user.groups.clear()
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)
        user.user_permissions.add(Permission.objects.get(content_type__app_label="mgmt", codename="view_dischargedestination"))
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            user.__dict__.pop(cache_name, None)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{"id": active.pk, "name": "Nach Hause"}])
        user.user_permissions.add(Permission.objects.get(content_type__app_label="mgmt", codename="add_dischargedestination"))
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            user.__dict__.pop(cache_name, None)
        self.assertEqual(self.client.post(url, {"name": "Eigener Vorschlag"}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
