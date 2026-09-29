from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelTests(TestCase):
    def test_create_user(self):
        user = get_user_model().objects.create_user(
            username='dispatcher',
            password='secure-password',
        )

        self.assertEqual(user.username, 'dispatcher')
        self.assertTrue(user.check_password('secure-password'))
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='secure-password',
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
