from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("perfil/", views.perfil_view, name="perfil"),

    # Autenticação
    path("login/", auth_views.LoginView.as_view(
        template_name="registration/login.html",
        redirect_authenticated_user=True
    ), name="login"),

    path("logout/", auth_views.LogoutView.as_view(
        next_page="login"
    ), name="logout"),

    path("signup/", views.signup, name="signup"),

    
    path(
        "alterar-senha/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url="/conta/alterar-senha/sucesso/"
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
