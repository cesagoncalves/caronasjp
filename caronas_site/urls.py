from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('viagens.urls')),

    # Autenticação padrão do Django (login, logout, reset de senha)
    path('', include('django.contrib.auth.urls')),

    # Rotas do seu app de usuários
    path('', include('usuarios.urls')),

    # Rotas do django-allauth (login social)
    path('accounts/', include('allauth.urls')),

    # Service worker
    path(
        "sw.js",
        TemplateView.as_view(template_name="sw.js", content_type="application/javascript"),
        name="service_worker",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
