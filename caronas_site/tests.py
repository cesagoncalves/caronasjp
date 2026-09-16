from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings


@override_settings(ALLOWED_HOSTS=["testserver"], SECURE_SSL_REDIRECT=False)
class HealthCheckTests(SimpleTestCase):
    # SimpleTestCase forbids database queries; block opening connections too.
    def test_probes_do_not_connect_to_database_even_with_session_cookie(self):
        self.client.cookies[settings.SESSION_COOKIE_NAME] = "a" * 32
        with patch(
            "django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection",
            side_effect=AssertionError("Health check must not connect to database"),
        ):
            for path in ("/healthz", "/healthz/"):
                for method in ("get", "head"):
                    with self.subTest(path=path, method=method):
                        response = getattr(self.client, method)(path)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.content, b"ok" if method == "get" else b"")
                        self.assertEqual(response["Content-Type"], "text/plain")
                        self.assertEqual(response["Cache-Control"], "no-store")
                        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)

    def test_other_paths_continue_through_application(self):
        response = self.client.get("/healthz-not-found/")
        self.assertEqual(response.status_code, 404)
