from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

urlpatterns = [
    path("perfil/", views.perfil_view, name="perfil"),
    path("excluir-conta/", views.excluir_conta, name="excluir_conta"),

    # Autenticação
    path("login/", auth_views.LoginView.as_view(
        template_name="registration/login.html",
        redirect_authenticated_user=True
    ), name="login"),

    path("logout/", auth_views.LogoutView.as_view(
        next_page="login"
    ), name="logout"),

    path("signup/", views.signup, name="signup"),
    path("completar-perfil/", views.completar_perfil, name="completar_perfil"),
    path("push/subscribe/", views.push_subscribe, name="push_subscribe"),
    path("push/unsubscribe/", views.push_unsubscribe, name="push_unsubscribe"),
    path("push/skip/", views.push_skip, name="push_skip"),

    
    path(
        "alterar-senha/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url=reverse_lazy("lista_caronas")
        ),
        name="alterar_senha"
    ),
    path(
        "alterar-senha/sucesso/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done"
    ),
]
