from django.http import HttpResponse


class HealthCheckMiddleware:
    """Answer liveness probes before session/auth middleware can access the DB."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info in {"/healthz", "/healthz/"}:
            response = HttpResponse("ok", content_type="text/plain")
            response["Cache-Control"] = "no-store"
            return response
        return self.get_response(request)
