from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest ,HttpResponse
from django.db.models import Sum, Count, Q
from .models import Carona, Solicitacao, Veiculo, Notificacao
from .forms import CaronaForm, SolicitacaoForm, VeiculoForm
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
import json
from django.utils import timezone



def lista_caronas(request):
    caronas = (
        Carona.objects
        .filter(status='ativa')
        .annotate(
            aguardando_confirmacao=Count(
                'solicitacoes',
                filter=Q(solicitacoes__status='pendente')
            )
        )
        .order_by('-criado_em')
    )

    origem = request.GET.get('origem')
    destino = request.GET.get('destino')
    data = request.GET.get('data')

    if origem:
        caronas = caronas.filter(origem__icontains=origem)
    if destino:
        caronas = caronas.filter(destino__icontains=destino)
    if data:
        caronas = caronas.filter(data=data)

    for carona in caronas:
        carona.passageiros_aceitos = carona.solicitacoes.filter(status='aceita')

    return render(request, 'viagens/lista.html', {
        'caronas': caronas,
        'origem': origem or "",
        'destino': destino or "",
        'data': data or "",
    })


@login_required
def criar_carona(request):
    if request.method == "POST":
        carona_form = CaronaForm(request.POST, user=request.user)
        veiculo_form = VeiculoForm()

        if carona_form.is_valid():
            carona = carona_form.save(commit=False)
            carona.motorista = request.user
            carona.save()
            return redirect("lista_caronas")

    else:
        carona_form = CaronaForm(user=request.user)
        veiculo_form = VeiculoForm()

    return render(
        request,
        "viagens/criar.html",
        {
            "form": carona_form,
            "veiculo_form": veiculo_form,
        }
    )


@login_required
def editar_carona(request, carona_id):
    carona = get_object_or_404(Carona, id=carona_id)

    if carona.motorista != request.user:
        return HttpResponseForbidden("Você não pode editar esta carona.")

    # 📸 Snapshot do estado antigo (somente o que importa)
    estado_antigo = {
        "origem": carona.origem,
        "destino": carona.destino,
        "data": carona.data,
        "hora": carona.hora,
        "vagas": carona.vagas,
        "valor": carona.valor_exibicao,  
        "veiculo_id": carona.veiculo_id,
    }

    if request.method == "POST":
        form = CaronaForm(
            request.POST,
            request.FILES,
            instance=carona
        )

        if form.is_valid():
            form.save()

            alteracoes = []

            if estado_antigo["origem"] != carona.origem:
                alteracoes.append("Origem")

            if estado_antigo["destino"] != carona.destino:
                alteracoes.append("Destino")

            if estado_antigo["data"] != carona.data:
                alteracoes.append("Data")

            if estado_antigo["hora"] != carona.hora:
                alteracoes.append("Horário")

            if estado_antigo["vagas"] != carona.vagas:
                alteracoes.append("Vagas")

            if estado_antigo["valor"] != carona.valor_exibicao:
                alteracoes.append("Valor")

            if estado_antigo["veiculo_id"] != carona.veiculo_id:
                alteracoes.append("Veículo")

            if alteracoes:

                carona.viagem_atualizada = True
                carona.data_edicao = timezone.now()
                carona.save(update_fields=["viagem_atualizada", "data_edicao"])
                
                solicitacoes_aceitas = carona.solicitacoes.filter(status="aceita")

                for s in solicitacoes_aceitas:
                    # Marca como atualizada (isso é o gatilho do badge)
                    s.viagem_atualizada = True
                    s.data_edicao = timezone.now()
                    s.save(update_fields=["viagem_atualizada", "data_edicao"])

                for s in solicitacoes_aceitas:
                    print("DEBUG:", s.id, s.uuid_local, s.solicitante)
                    if s.solicitante:
                        Notificacao.objects.create(
                            usuario=s.solicitante,
                            tipo="viagem_atualizada",
                            titulo="Carona atualizada 🚗",
                            mensagem="O motorista alterou informações da viagem.",
                            carona=carona,
                            solicitacao=s,
                        )

                    if s.uuid_local:
                        s.viagem_atualizada = True
                        s.save(update_fields=["viagem_atualizada"])

            messages.success(request, "Carona atualizada com sucesso.")
            return redirect("minhas_caronas")

    else:
        form = CaronaForm(instance=carona)

    veiculo_form = VeiculoForm()

    return render(
        request,
        "viagens/editar_carona.html",
        {
            "form": form,
            "carona": carona,
            "veiculo_form": veiculo_form,
        }
    )




@login_required
def excluir_carona(request, carona_id):
    carona = get_object_or_404(
        Carona,
        id=carona_id,
        motorista=request.user
    )

    passageiros_aceitos = carona.solicitacoes.filter(status='aceita').exists()

    if request.method == "POST":
        if passageiros_aceitos:
            carona.status = 'cancelada'
            carona.save()

            for s in carona.solicitacoes.filter(status__in=['aceita', 'pendente']):
                if s.solicitante:
                    Notificacao.objects.create(
                        usuario=s.solicitante,
                        tipo="viagem_cancelada",
                        titulo="Carona cancelada",
                        mensagem="A carona foi cancelada pelo motorista.",
                        carona=carona,
                        solicitacao=s,
                    )

            carona.solicitacoes.filter(
                status__in=['aceita', 'pendente']
            ).update(status='cancelada')
        else:
            carona.delete()

        return redirect("minhas_caronas")

    return render(request, "viagens/excluir_carona.html", {
        "carona": carona,
        "tem_passageiros": passageiros_aceitos
    })


def solicitar_vaga(request, carona_id):
    carona = get_object_or_404(Carona, id=carona_id)

    vagas_ocupadas = carona.solicitacoes.filter(status="aceita").aggregate(
        total=Sum("quantidade")
    )["total"] or 0
    vagas_restantes = carona.vagas - vagas_ocupadas

    if request.method == "POST":
        form = SolicitacaoForm(request.POST)

        if form.is_valid():
            quantidade_pedida = form.cleaned_data["quantidade"]

            if quantidade_pedida > vagas_restantes:
                messages.error(
                    request,
                    f"Só restam {vagas_restantes} vaga(s) disponíveis!"
                )
                return render(request, "viagens/solicitar_vaga.html", {
                    "form": form,
                    "carona": carona,
                    "vagas_restantes": vagas_restantes
                })

            if request.user.is_authenticated:
                form.instance.solicitante = request.user

            uuid_local = request.POST.get("uuid_local")

            form.instance.carona = carona
            form.instance.status = "pendente"

            if not request.user.is_authenticated:
                form.instance.uuid_local = uuid_local
            solicitacao = form.save()
            print(
                "DEBUG SOLICITAÇÃO:",
                solicitacao.id,
                solicitacao.uuid_local,
                solicitacao.solicitante
            )

            # 🚨 VISITANTE (SEM LOGIN)
            if not request.user.is_authenticated:
                return render(request, "viagens/solicitacao_salva_local.html", {
                    "carona": carona,
                    "solicitacao": solicitacao,
                    "solicitacao_id": solicitacao.id, 
                    "quantidade": solicitacao.quantidade,
                    "status": solicitacao.status,
                })
            
            # 🔔 NOTIFICA MOTORISTA (usuário logado)
            if request.user.is_authenticated:
                if solicitacao.solicitante:
                    Notificacao.objects.create(
                        usuario=carona.motorista,
                        tipo="solicitacao_recebida",
                        titulo="Nova solicitação de carona",
                        mensagem=f"{solicitacao.nome_solicitante} solicitou {solicitacao.quantidade} vaga(s).",
                        carona=carona,
                        solicitacao=solicitacao,
                    )

            # 👤 USUÁRIO LOGADO
            messages.success(
                request,
                "Solicitação enviada com sucesso! Aguarde o motorista aceitar 🚗✨"
            )
            return redirect("lista_caronas")

    else:
        if request.user.is_authenticated:
            form = SolicitacaoForm(initial={
                "nome_solicitante": request.user.nome_completo or request.user.email,
                "telefone_solicitante": request.user.telefone,
            })
        else:
            form = SolicitacaoForm()

    return render(request, "viagens/solicitar_vaga.html", {
        "form": form,
        "carona": carona,
        "vagas_restantes": vagas_restantes
    })



@login_required
def aceitar_solicitacao(request, solicitacao_id):
    solicitacao = get_object_or_404(Solicitacao, id=solicitacao_id)

    if solicitacao.carona.motorista != request.user:
        return redirect("lista_caronas")

    if solicitacao.status == "aceita":
        messages.info(request, "Essa solicitação já foi aceita.")
        return redirect("gerenciar_solicitacoes")

    vagas_ocupadas = solicitacao.carona.solicitacoes.filter(
        status="aceita"
    ).aggregate(total=Sum("quantidade"))["total"] or 0

    vagas_restantes = solicitacao.carona.vagas - vagas_ocupadas

    if solicitacao.quantidade > vagas_restantes:
        messages.error(request, f"Só restam {vagas_restantes} vaga(s)!")
        return redirect("gerenciar_solicitacoes")

    solicitacao.status = "aceita"
    solicitacao.save()
    if solicitacao.solicitante:

        Notificacao.objects.create(
            usuario=solicitacao.solicitante,
            tipo="viagem_aceita",
            titulo="Viagem confirmada 🚗",
            mensagem=(
                f"Sua viagem {solicitacao.carona.origem} → "
                f"{solicitacao.carona.destino} foi confirmada."
            ),
            carona=solicitacao.carona,
            solicitacao=solicitacao,
    )

    messages.success(request, "Solicitação aceita com sucesso! 🎉")

    return redirect("gerenciar_solicitacoes")


@login_required
def gerenciar_solicitacoes(request):
    solicitacoes = Solicitacao.objects.filter(
        carona__motorista=request.user,
        status='pendente'
    ).order_by('-data_solicitacao')
    
    return render(request, "viagens/gerenciar_solicitacoes.html", {
        "solicitacoes": solicitacoes,
    })

@login_required
def recusar_solicitacao(request, solicitacao_id):
    solicitacao = get_object_or_404(Solicitacao, id=solicitacao_id)

    if solicitacao.carona.motorista != request.user:
        return redirect("lista_caronas")

    solicitacao.status = "recusada"
    solicitacao.save()
    if solicitacao.solicitante:
        Notificacao.objects.create(
            usuario=solicitacao.solicitante,
            tipo="solicitacao_recusada",
            titulo="Solicitação recusada",
            mensagem="O motorista recusou sua solicitação de carona.",
            carona=solicitacao.carona,
            solicitacao=solicitacao,
        )

    messages.success(request, "Solicitação recusada! 🚫")
    return redirect("gerenciar_solicitacoes")


def minhas_solicitacoes(request):

    if request.user.is_authenticated:

        Notificacao.objects.filter(
            usuario=request.user,
            tipo__in=["solicitacao_recusada"],
            lida=False
        ).update(lida=True)
        
        minhas = Solicitacao.objects.filter(
            solicitante=request.user
        ).order_by('-data_solicitacao')

        return render(request, 'viagens/minhas_solicitacoes.html', {
            'solicitacoes': minhas,
            'modo': 'bd'
        })

    return render(request, 'viagens/minhas_solicitacoes.html', {
        'solicitacoes': [],
        'modo': 'local'
    })



def minhas_viagens(request):

    if request.user.is_authenticated:

        Notificacao.objects.filter(
            usuario=request.user,
            tipo__in=["viagem_atualizada", "viagem_aceita", "viagem_cancelada", "viagem_concluida"],
            lida=False
        ).update(lida=True)

        viagens = Solicitacao.objects.filter(
            solicitante=request.user,
            status='aceita',
            carona__status='ativa'  
        ).select_related('carona').order_by('-data_solicitacao')


        return render(request, 'viagens/minhas_viagens.html', {
            'viagens': viagens,
            'modo': 'bd'
        })

    return render(request, 'viagens/minhas_viagens.html', {
        'viagens': [],
        'modo': 'local'
    })


def cancelar_solicitacao(request, id):
    s = get_object_or_404(
        Solicitacao,
        id=id,
        solicitante=request.user
    )

    with transaction.atomic():

        if s.status == "pendente":
            s.delete()
            return redirect("minhas_solicitacoes")

        if s.status == "aceita":
            s.mudar_status("cancelada")
            return redirect("minhas_viagens")

    return redirect("minhas_solicitacoes")

@require_POST
def cancelar_solicitacao_publica(request, id):
    token = request.POST.get("token")

    if not token:
        return HttpResponseBadRequest("Token não informado")

    solicitacao = get_object_or_404(
        Solicitacao,
        id=id,
        token_cancelamento=token
    )

    with transaction.atomic():

        if solicitacao.status == "pendente":
            solicitacao.delete()
            return HttpResponse(status=204)

        if solicitacao.status == "aceita":
            solicitacao.mudar_status("cancelada")
            return HttpResponse(status=204)

    return HttpResponseBadRequest("Solicitação não pode ser cancelada")



def api_status_solicitacoes(request):
    """
    Retorna o status atualizado das solicitações.
    Para usuários deslogados, usa carona_id + quantidade.
    """

    ids_param = request.GET.get("ids", "")
    caronas_param = request.GET.get("caronas", "")

    result = []

    # 🔹 IDs reais (logado ou local salvo)
    if ids_param:
        lista_ids = [i for i in ids_param.split(",") if i.isdigit()]
        solicitacoes = (
            Solicitacao.objects
            .select_related("carona")
            .filter(id__in=lista_ids)
        )

        for s in solicitacoes:
            result.append({
                "id": s.id,
                "carona_id": s.carona.id,
                "quantidade": s.quantidade,
                "status": s.status,
                "carona_status": s.carona.status,
                "viagem_atualizada": s.viagem_atualizada,
                 "data_edicao": (
                    s.data_edicao.isoformat()
                    if s.data_edicao
                    else None
                ),
            })

    # 🔹 carona_id + quantidade (usuário deslogado)
    elif caronas_param:
        pares = [p for p in caronas_param.split(",") if ":" in p]

        for par in pares:
            try:
                carona_id_str, quantidade_str = par.split(":")
                carona_id = int(carona_id_str)
                quantidade = int(quantidade_str)
            except ValueError:
                continue

            solicitacao = (
                Solicitacao.objects
                .select_related("carona")
                .filter(carona_id=carona_id, quantidade=quantidade)
                .order_by("-data_solicitacao")
                .first()
            )

            if solicitacao:
                result.append({
                    "id": solicitacao.id,
                    "carona_id": solicitacao.carona.id,
                    "quantidade": solicitacao.quantidade,
                    "status": solicitacao.status,
                    "carona_status": solicitacao.carona.status, 
                    "viagem_atualizada": solicitacao.viagem_atualizada,
                        "data_edicao": (
                            solicitacao.data_edicao.isoformat()
                            if solicitacao.data_edicao
                            else None
                        ),
                })

    return JsonResponse({"result": result})

@login_required
def criar_veiculo(request):
    if request.method == "POST":
        form = VeiculoForm(request.POST)
        if form.is_valid():
            veiculo = form.save(commit=False)
            veiculo.motorista = request.user
            veiculo.save()

            return JsonResponse({
                "id": veiculo.id,
                "label": str(veiculo),
            })

        return JsonResponse({"errors": form.errors}, status=400)
    
@login_required
def meus_veiculos(request):
    veiculos = Veiculo.objects.filter(motorista=request.user)
    return render(
        request,
        "viagens/meus_veiculos.html",
        {"veiculos": veiculos}
    )

@login_required
def editar_veiculo(request, veiculo_id):
    veiculo = get_object_or_404(
        Veiculo,
        id=veiculo_id,
        motorista=request.user
    )

    if request.method == "POST":
        form = VeiculoForm(request.POST, instance=veiculo)
        if form.is_valid():
            form.save()
            messages.success(request, "Veículo atualizado com sucesso.")
        else:
            messages.error(request, "Erro ao atualizar veículo.")

    return redirect("meus_veiculos")

@login_required
def excluir_veiculo(request, veiculo_id):
    veiculo = get_object_or_404(
        Veiculo,
        id=veiculo_id,
        motorista=request.user
    )

    veiculo.delete()
    messages.success(request, "Veículo excluído com sucesso.")
    return redirect("meus_veiculos")

@login_required
def concluir_carona(request, carona_id):
    carona = get_object_or_404(Carona, id=carona_id, motorista=request.user)

    carona.status = 'concluida'
    carona.save()

    return redirect('lista_caronas')


def historico_viagens(request):
    tipo = request.GET.get('tipo', 'todas')
    caronas = Carona.objects.none()
    solicitacoes = None

    # ===== USUÁRIO LOGADO =====
    if request.user.is_authenticated:
        base_filter = Q(status='concluida')

        if tipo == 'motorista':
            filtro = base_filter & Q(motorista=request.user)

        elif tipo == 'passageiro':
            filtro = base_filter & Q(
                solicitacoes__solicitante=request.user,
                solicitacoes__status='aceita'
            )

        else:
            filtro = base_filter & (
                Q(motorista=request.user) |
                Q(solicitacoes__solicitante=request.user, solicitacoes__status='aceita')
            )

        caronas = (
            Carona.objects
            .filter(filtro)
            .distinct()
            .order_by('-data', '-hora')
        )

    # ===== USUÁRIO DESLOGADO =====
    else:
        uuid_local = request.GET.get("uuid")

        if uuid_local:
            solicitacoes = (
                Solicitacao.objects
                .select_related("carona")
                .filter(uuid_local=uuid_local)
                .order_by('-data_solicitacao')
            )

    return render(request, "viagens/historico.html", {
        "caronas": caronas,
        "solicitacoes": solicitacoes,
        "tipo": tipo,
    })

def api_estado_caronas(request):
    ids = request.GET.get("ids", "")
    result = []

    if ids:
        carona_ids = [i for i in ids.split(",") if i.isdigit()]
        caronas = Carona.objects.filter(id__in=carona_ids)

        for c in caronas:
            result.append({
                "id": c.id,
                "origem": c.origem,
                "destino": c.destino,
                "data": c.data.strftime("%Y-%m-%d"),
                "hora": c.hora.strftime("%H:%M"),
                "motorista_nome": c.motorista.nome_curto or c.motorista.nome_completo,
                "status": c.status
            })

    return JsonResponse({ "result": result })

@login_required
def minhas_caronas_view(request):

    Notificacao.objects.filter(
            usuario=request.user,
            tipo__in=["passageiro_cancelou","viagem_cancelada"],
            lida=False
        ).update(lida=True)

    caronas = (
        Carona.objects
        .filter(
            motorista=request.user,
            status='ativa' 
        )
        .order_by('-criado_em')
    )

    for carona in caronas:
        carona.passageiros_aceitos = carona.solicitacoes.filter(status='aceita')

    return render(request, "viagens/minhas_caronas.html", {
        "caronas": caronas
    })

@login_required
def remover_passageiro(request, pk):
    solicitacao = get_object_or_404(Solicitacao, pk=pk)

    if solicitacao.carona.motorista != request.user:
        return redirect("home")

    solicitacao.status = "cancelada"
    solicitacao.save()
    
    if solicitacao.solicitante:
        Notificacao.objects.create(
            usuario=solicitacao.solicitante,
            tipo="viagem_cancelada",
            titulo="Você foi removido da carona",
            mensagem="O motorista removeu você da carona.",
            carona=solicitacao.carona,
            solicitacao=solicitacao,
        )

    return redirect(request.META.get("HTTP_REFERER", "home"))

@login_required
def marcar_notificacoes_como_lidas(request):
    Notificacao.objects.filter(
        usuario=request.user,
        lida=False
    ).update(lida=True)

    return JsonResponse({"status": "ok"})
