from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, login
from django.contrib.auth import get_user_model
from django.contrib import messages

from .forms import UsuarioProfileForm, UsuarioPasswordForm, UsuarioCreationForm
from viagens.models import Carona

Usuario = get_user_model()


@login_required
def perfil_view(request):
    usuario = request.user

    if request.method == "POST":
        form = UsuarioProfileForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            form.save()
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
            login(request, usuario)
            messages.success(request, "Conta criada com sucesso! Bem-vindo 😄")
            return redirect("lista_caronas")
    else:
        form = UsuarioCreationForm()

    return render(request, "usuarios/cadastro.html", {"form": form})
