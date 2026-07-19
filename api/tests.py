from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from api.auth_views import SYSTEM_STUDENT_EMAIL_MESSAGE
from api.models import Enrol, LoginPIN


class RequestPinTests(TestCase):
    def test_system_student_email_does_not_send_pin(self):
        user = get_user_model().objects.create_user(
            username="ane@ifct0209.es",
            email="ane@ifct0209.es",
            password="teacher-gave-this",
        )
        Enrol.objects.create(user=user, codigo="IFCT0209", role="student")

        with patch("api.auth_views.send_mail") as send_mail:
            response = self.client.post(
                "/v5/auth/request_pin",
                data={"email": "ane@ifct0209.es"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], SYSTEM_STUDENT_EMAIL_MESSAGE)
        self.assertFalse(LoginPIN.objects.filter(email="ane@ifct0209.es").exists())
        send_mail.assert_not_called()
