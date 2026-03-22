from django.shortcuts import redirect
from django.urls import reverse


class CompleteProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        path = request.path or ""

        if user and user.is_authenticated:
            allowed_prefixes = (
                "/admin/",
                "/accounts/",
                "/static/",
                "/media/",
            )
            allowed_paths = {
                reverse("login"),
                reverse("logout"),
                reverse("signup"),
                reverse("alterar_senha"),
                reverse("password_change_done"),
                reverse("completar_perfil"),
                reverse("push_subscribe"),
                reverse("push_unsubscribe"),
                reverse("push_skip"),
                "/favicon.ico",
            }

            if not path.startswith(allowed_prefixes) and path not in allowed_paths:
                if user.socialaccount_set.exists() and (not user.nome_completo or not user.telefone):
                    return redirect("completar_perfil")

        return self.get_response(request)
