import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse

from .forms import UsuarioProfileForm, UsuarioPasswordForm, UsuarioCreationForm, UsuarioCompleteProfileForm
from .models import PushSubscription
from viagens.models import Carona, Solicitacao, Notificacao

Usuario = get_user_model()


def _cancelar_itens_ativos_antes_exclusao(usuario):
    # Motorista: cancela caronas ativas e notifica passageiros/solicitantes.
    caronas_ativas = Carona.objects.filter(motorista=usuario, status="ativa")
    for carona in caronas_ativas:
        solicitacoes_ativas = carona.solicitacoes.filter(status__in=["pendente", "aceita"])
        for solicitacao in solicitacoes_ativas:
            if solicitacao.solicitante and solicitacao.solicitante_id != usuario.id:
                Notificacao.objects.create(
                    usuario=solicitacao.solicitante,
                    tipo="viagem_cancelada",
                    titulo=(
                        "Entrega cancelada"
                        if solicitacao.tipo == "encomenda"
                        else "Viagem cancelada"
                    ),
                    mensagem=(
                        "A entrega foi cancelada porque o motorista excluiu a conta."
                        if solicitacao.tipo == "encomenda"
                        else "A viagem foi cancelada porque o motorista excluiu a conta."
                    ),
                )
            solicitacao.status = "cancelada"
            solicitacao.save(update_fields=["status"])

        carona.status = "cancelada"
        carona.save(update_fields=["status"])

    # Passageiro/remetente: cancela participacoes/encomendas ativas e notifica motoristas.
    minhas_solicitacoes_ativas = Solicitacao.objects.filter(
        solicitante=usuario,
        status__in=["pendente", "aceita"],
        carona__status="ativa",
    ).select_related("carona", "carona__motorista")

    for solicitacao in minhas_solicitacoes_ativas:
        if solicitacao.carona.motorista_id != usuario.id:
            Notificacao.objects.create(
                usuario=solicitacao.carona.motorista,
                tipo="passageiro_cancelou",
                titulo=(
                    "Passageiro cancelou encomenda"
                    if solicitacao.tipo == "encomenda"
                    else "Passageiro cancelou"
                ),
                mensagem=(
                    "Uma encomenda foi cancelada porque o usuario excluiu a conta."
                    if solicitacao.tipo == "encomenda"
                    else "Uma solicitacao de carona foi cancelada porque o usuario excluiu a conta."
                ),
            )
        solicitacao.status = "cancelada"
        solicitacao.save(update_fields=["status"])


@login_required
def perfil_view(request):
    usuario = request.user

    if request.method == "POST":
        form = UsuarioProfileForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            usuario = form.save(commit=False)
            nova_foto = request.FILES.get("foto")
            if nova_foto:
                usuario.foto = nova_foto
            usuario.save()
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect("perfil")
    else:
        form = UsuarioProfileForm(instance=usuario)

    return render(request, "usuarios/perfil.html", {"form": form})



def signup(request):
    if request.method == "POST":
        form = UsuarioCreationForm(request.POST, request.FILES)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Conta criada com sucesso! Bem-vindo 😄")
            return redirect("lista_caronas")
    else:
        form = UsuarioCreationForm()

    return render(request, "usuarios/cadastro.html", {"form": form})


@login_required
def completar_perfil(request):
    usuario = request.user
    if usuario.nome_completo and usuario.telefone:
        return redirect("lista_caronas")

    if request.method == "POST":
        form = UsuarioCompleteProfileForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect("lista_caronas")
    else:
        form = UsuarioCompleteProfileForm(instance=usuario)

    return render(request, "usuarios/completar_perfil.html", {"form": form})


@login_required
@require_POST
def push_subscribe(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        endpoint = payload.get("endpoint")
        keys = payload.get("keys", {})
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)

    if not endpoint or not p256dh or not auth:
        return JsonResponse({"ok": False, "error": "missing_fields"}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
        },
    )

    request.session["ask_push_permission"] = False

    return JsonResponse({"ok": True})


@login_required
@require_POST
def push_unsubscribe(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        endpoint = payload.get("endpoint")
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)

    if endpoint:
        PushSubscription.objects.filter(endpoint=endpoint, user=request.user).delete()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def push_skip(request):
    request.session["ask_push_permission"] = False
    return JsonResponse({"ok": True})


@login_required
@require_POST
def excluir_conta(request):
    usuario = request.user
    with transaction.atomic():
        _cancelar_itens_ativos_antes_exclusao(usuario)
        logout(request)
        usuario.delete()
    messages.success(request, "Conta excluida com sucesso.")
    return redirect("login")
