from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections, DatabaseError
from django.db.utils import OperationalError


class CompleteProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
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

        if path.startswith(allowed_prefixes) or path in allowed_paths:
            return self.get_response(request)

        try:
            user = request.user
            if user.is_authenticated:
                if user.socialaccount_set.exists() and (not user.nome_completo or not user.telefone):
                    return redirect("completar_perfil")
        except (OperationalError, DatabaseError):
            close_old_connections()
            request._cached_user = AnonymousUser()
        except Exception:
            return self.get_response(request)

        return self.get_response(request)
