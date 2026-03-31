from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest ,HttpResponse
from django.db.models import Sum, Count, Q, Max
from .models import Carona, Solicitacao, Veiculo, Notificacao
from usuarios.models import PushSubscription
from .forms import CaronaForm, SolicitacaoForm, EncomendaForm, VeiculoForm
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.utils.html import format_html
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from difflib import SequenceMatcher
import re
import unicodedata
import json
from django.utils import timezone


def _destino_notificacao(notificacao):
    solicitacao = notificacao.solicitacao
    carona = notificacao.carona or (solicitacao.carona if solicitacao else None)
    tipo_solicitacao = solicitacao.tipo if solicitacao else None

    if notificacao.tipo == "solicitacao_recebida":
        if solicitacao and tipo_solicitacao == "encomenda":
            return redirect("detalhe_encomenda", encomenda_id=solicitacao.id)
        return redirect("gerenciar_solicitacoes")

    if notificacao.tipo == "solicitacao_recusada":
        if tipo_solicitacao == "encomenda":
            return redirect("minhas_encomendas_passageiro")
        return redirect("minhas_solicitacoes")

    if notificacao.tipo in ["viagem_aceita", "viagem_cancelada"]:
        if tipo_solicitacao == "encomenda":
            return redirect("minhas_encomendas_passageiro")
        return redirect("minhas_viagens")

    if notificacao.tipo == "viagem_atualizada":
        return redirect("minhas_viagens")

    if notificacao.tipo == "viagem_concluida":
        return redirect("historico_viagens")

    if notificacao.tipo == "passageiro_cancelou":
        if tipo_solicitacao == "encomenda":
            return redirect("minhas_encomendas")
        return redirect("minhas_caronas")

    return redirect("lista_caronas")


@login_required
def abrir_notificacao(request, notificacao_id):
    notificacao = get_object_or_404(Notificacao, id=notificacao_id, usuario=request.user)
    if not notificacao.lida:
        notificacao.lida = True
        notificacao.save(update_fields=["lida"])
    return _destino_notificacao(notificacao)



def lista_caronas(request):
    def _juntar_itens_humanos(itens):
        if not itens:
            return ""
        if len(itens) == 1:
            return itens[0]
        if len(itens) == 2:
            return f"{itens[0]} e {itens[1]}"
        return f"{', '.join(itens[:-1])} e {itens[-1]}"

    def normalizar_texto(valor):
        base = (valor or "").strip().lower()
        if not base:
            return ""
        sem_acento = "".join(
            ch for ch in unicodedata.normalize("NFD", base)
            if unicodedata.category(ch) != "Mn"
        )
        sem_pontuacao = re.sub(r"[^a-z0-9\s]", " ", sem_acento)
        return re.sub(r"\s+", " ", sem_pontuacao).strip()

    def gerar_sigla(valor):
        stopwords = {"de", "da", "do", "das", "dos", "e"}
        tokens = [t for t in normalizar_texto(valor).split() if t and t not in stopwords]
        return "".join(token[0] for token in tokens)

    def match_cidade(consulta, valor_cidade):
        consulta_n = normalizar_texto(consulta)
        cidade_n = normalizar_texto(valor_cidade)
        if not consulta_n:
            return True
        if not cidade_n:
            return False

        if consulta_n in cidade_n:
            return True

        sigla = gerar_sigla(valor_cidade)
        if consulta_n == sigla or (len(consulta_n) <= 4 and sigla.startswith(consulta_n)):
            return True

        palavras = cidade_n.split()
        if len(consulta_n.split()) == 1:
            if any(p.startswith(consulta_n) for p in palavras):
                return True
        else:
            termos = consulta_n.split()
            if all(any(p.startswith(t) for p in palavras) for t in termos):
                return True

        # Fallback leve para erro de digitação.
        if len(consulta_n) >= 4:
            similaridade = SequenceMatcher(None, consulta_n, cidade_n).ratio()
            if similaridade >= 0.72:
                return True

        return False

    def preencher_dados_carona(carona):
        if not carona:
            return None
        if carona.veiculo:
            if carona.veiculo.tipo == "van":
                carona.veiculo_card = "Van"
            elif carona.veiculo.tipo == "onibus":
                carona.veiculo_card = "Onibus"
            else:
                carona.veiculo_card = carona.veiculo.modelo
        else:
            carona.veiculo_card = ""
            
        carona.aguardando_confirmacao = carona.solicitacoes.filter(
            status="pendente",
            tipo="carona",
        ).count()
        carona.pendencias_motorista = carona.solicitacoes.filter(status="pendente").count()
        carona.passageiros_aceitos = carona.solicitacoes.filter(status="aceita", tipo="carona")
        carona.passageiros_pendentes = carona.solicitacoes.filter(
            status="pendente",
            tipo="carona",
        ).select_related("solicitante")
        carona.encomendas_ativas_lista = carona.solicitacoes.filter(
            tipo="encomenda",
            status__in=["pendente", "aceita"]
        ).select_related("solicitante")
        carona.encomendas_pendentes = carona.solicitacoes.filter(tipo="encomenda", status="pendente").count()
        carona.encomendas_ativas = carona.solicitacoes.filter(
            tipo="encomenda",
            status="aceita"
        ).count()

        if request.user.is_authenticated and request.user != carona.motorista:
            carona.minha_solicitacao_ativa = carona.solicitacoes.filter(
                solicitante=request.user,
                tipo="carona",
                status="aceita",
            ).first()
            carona.minha_solicitacao_pendente = carona.solicitacoes.filter(
                solicitante=request.user,
                tipo="carona",
                status="pendente",
            ).first()
            carona.minhas_encomendas_aceitas_count = carona.solicitacoes.filter(
                solicitante=request.user,
                tipo="encomenda",
                status="aceita",
            ).count()
            carona.minhas_encomendas_pendentes_count = carona.solicitacoes.filter(
                solicitante=request.user,
                tipo="encomenda",
                status="pendente",
            ).count()
            carona.minhas_encomendas_ativas = carona.solicitacoes.filter(
                solicitante=request.user,
                tipo="encomenda",
                status__in=["pendente", "aceita"],
            ).order_by("-data_solicitacao")
            carona.minhas_encomendas_ativas_count = carona.minhas_encomendas_ativas.count()
            carona.minha_participacao_pendente = bool(
                carona.minha_solicitacao_pendente
                or carona.minhas_encomendas_pendentes_count > 0
            )
        else:
            carona.minha_solicitacao_ativa = None
            carona.minha_solicitacao_pendente = None
            carona.minhas_encomendas_ativas = []
            carona.minhas_encomendas_aceitas_count = 0
            carona.minhas_encomendas_pendentes_count = 0
            carona.minhas_encomendas_ativas_count = 0
            carona.minha_participacao_pendente = False
        return carona

    # somente caronas ativas e que ainda não partiram
    agora = timezone.localtime(timezone.now())
    data_atual = agora.date()
    hora_atual = agora.time()
    caronas = (
        Carona.objects
        .filter(status='ativa')
        .filter(
            Q(data__gt=data_atual) |
            Q(data=data_atual, hora__gte=hora_atual)
        )
        .annotate(
            aguardando_confirmacao=Count(
                'solicitacoes',
                filter=Q(solicitacoes__status='pendente', solicitacoes__tipo='carona')
            )
        )
        .order_by('data', 'hora', '-criado_em')
    )

    origem = request.GET.get('origem')
    destino = request.GET.get('destino')
    data = request.GET.get('data')
    hora = request.GET.get('hora')
    vagas_min = request.GET.get("vagas_min")
    motorista = request.GET.get('motorista')
    tipos = request.GET.getlist("tipos")
    tipos_validos = [t for t in tipos if t in {"carro", "moto", "van", "onibus"}]
    vagas_min_valor = None
    if vagas_min:
        try:
            vagas_min_valor = max(int(vagas_min), 1)
        except (TypeError, ValueError):
            vagas_min_valor = None

    if data:
        caronas = caronas.filter(data=data)
    if hora:
        caronas = caronas.filter(hora__gte=hora)
    if motorista:
        caronas = caronas.filter(
            Q(motorista__nome_completo__icontains=motorista) |
            Q(motorista__email__icontains=motorista)
        )
    if tipos_validos:
        caronas = caronas.filter(veiculo__tipo__in=tipos_validos)

    if origem or destino:
        caronas = [
            c for c in caronas
            if (not origem or match_cidade(origem, c.origem))
            and (not destino or match_cidade(destino, c.destino))
        ]

    if vagas_min_valor:
        caronas = [c for c in caronas if c.vagas_restantes >= vagas_min_valor]

    partes_resumo = []
    if origem:
        partes_resumo.append(f"saindo de {origem}")
    if destino:
        partes_resumo.append(f"indo para {destino}")
    if motorista:
        partes_resumo.append(f"com motorista {motorista}")
    if data:
        data_ref = data
        if data_ref == timezone.localdate().isoformat():
            partes_resumo.append("hoje")
        else:
            try:
                partes_resumo.append(datetime.strptime(data_ref, "%Y-%m-%d").strftime("em %d/%m/%Y"))
            except ValueError:
                partes_resumo.append(f"em {data_ref}")
    if hora:
        partes_resumo.append(f"a partir de {hora}")
    if vagas_min_valor:
        partes_resumo.append(f"a partir de {vagas_min_valor} vaga(s)")
    if tipos_validos:
        labels_tipos = {
            "carro": "carro",
            "moto": "moto",
            "van": "van",
            "onibus": "onibus",
        }
        nomes = [labels_tipos[t] for t in tipos_validos]
        partes_resumo.append(f"tipo {_juntar_itens_humanos(nomes)}")

    resumo_filtros = ""
    if partes_resumo:
        resumo_filtros = "Buscando por viagens " + ", ".join(partes_resumo) + "."

    for carona in caronas:
        preencher_dados_carona(carona)

    destaques_ativos = []
    destaque_modais_extras = []

    if request.user.is_authenticated:
        destaques_map = {}

        def add_destaque(carona, tipo, data_ref, **extras):
            key = carona.id
            atual = destaques_map.get(key)
            if not atual:
                atual = {
                    "carona": preencher_dados_carona(carona),
                    "tipos": set(),
                    "data_ref": data_ref,
                }
                destaques_map[key] = atual

            atual["tipos"].add(tipo)
            if data_ref > atual["data_ref"]:
                atual["data_ref"] = data_ref

            if tipo == "passageiro" and extras.get("quantidade"):
                atual["quantidade"] = extras["quantidade"]

        caronas_motorista = Carona.objects.filter(motorista=request.user, status="ativa")
        for c in caronas_motorista:
            add_destaque(c, "motorista", c.criado_em)
            if c.solicitacoes.filter(tipo="encomenda", status="aceita").exists():
                ultima = (
                    c.solicitacoes.filter(tipo="encomenda", status="aceita")
                    .order_by("-data_solicitacao")
                    .first()
                )
                add_destaque(
                    c,
                    "entregar_encomenda",
                    ultima.data_solicitacao if ultima else c.criado_em,
                )

        solicitacoes_carona = (
            Solicitacao.objects
            .select_related("carona")
            .filter(
                solicitante=request.user,
                tipo="carona",
                status="aceita",
                carona__status="ativa",
            )
        )
        for s in solicitacoes_carona:
            add_destaque(s.carona, "passageiro", s.data_solicitacao, quantidade=s.quantidade)

        solicitacoes_encomenda = (
            Solicitacao.objects
            .select_related("carona")
            .filter(
                solicitante=request.user,
                tipo="encomenda",
                status="aceita",
                carona__status="ativa",
            )
        )
        for s in solicitacoes_encomenda:
            add_destaque(s.carona, "enviada", s.data_solicitacao)

        ordem_tipos = {
            "motorista": 1,
            "passageiro": 2,
            "entregar_encomenda": 3,
            "enviada": 4,
        }
        destaques_ativos = []
        for item in destaques_map.values():
            item["tipos"] = sorted(item["tipos"], key=lambda t: ordem_tipos.get(t, 99))
            destaques_ativos.append(item)

        destaques_ativos.sort(
            key=lambda x: (
                x["carona"].data,
                x["carona"].hora,
            ),
            reverse=False
        )

        if hasattr(caronas, "values_list"):
            carona_ids_tela = set(caronas.values_list("id", flat=True))
        else:
            carona_ids_tela = {c.id for c in caronas}
        vistos = set()
        for item in destaques_ativos:
            c = item["carona"]
            if c.id not in carona_ids_tela and c.id not in vistos:
                destaque_modais_extras.append(c)
                vistos.add(c.id)

    return render(request, 'viagens/lista.html', {
        'caronas': caronas,
        'origem': origem or "",
        'destino': destino or "",
        'data': data or "",
        'hora': hora or "",
        "vagas_min": vagas_min_valor or "",
        'motorista': motorista or "",
        "tipos_selecionados": tipos_validos,
        "resumo_filtros": resumo_filtros,
        "destaques_ativos": destaques_ativos,
        "destaque_modais_extras": destaque_modais_extras,
    })


@login_required
def criar_carona(request):
    datas_repeticao_post = []
    if request.method == "POST":
        carona_form = CaronaForm(request.POST, user=request.user)
        veiculo_form = VeiculoForm()
        datas_repeticao_post = request.POST.getlist("datas_repeticao")

        if carona_form.is_valid():
            carona_base = carona_form.save(commit=False)
            repetir_viagem = request.POST.get("repetir_viagem") == "on"
            if repetir_viagem:
                carona_base.data = timezone.localdate()
            carona_base.motorista = request.user
            carona_base.save()

            datas_repeticao = datas_repeticao_post
            criadas_repeticao = 0
            manter_carona_base = True

            if repetir_viagem:
                data_base = carona_base.data
                limite = data_base + timedelta(days=6)

                datas_validas = set()
                for valor_data in datas_repeticao:
                    try:
                        data_rep = datetime.strptime(valor_data, "%Y-%m-%d").date()
                    except (TypeError, ValueError):
                        continue

                    if data_base <= data_rep <= limite:
                        datas_validas.add(data_rep)

                if datas_repeticao:
                    manter_carona_base = data_base in datas_validas

                for data_rep in sorted(datas_validas):
                    if data_rep == data_base:
                        continue
                    Carona.objects.create(
                        origem=carona_base.origem,
                        destino=carona_base.destino,
                        data=data_rep,
                        hora=carona_base.hora,
                        vagas=carona_base.vagas,
                        motorista=request.user,
                        tipo_valor=carona_base.tipo_valor,
                        valor=carona_base.valor,
                        veiculo=carona_base.veiculo,
                        observacoes=carona_base.observacoes,
                    )
                    criadas_repeticao += 1

                if not manter_carona_base:
                    carona_base.delete()

            if criadas_repeticao > 0:
                total_viagens = criadas_repeticao + (1 if manter_carona_base else 0)
                messages.success(
                    request,
                    f"Carona criada com repeticao! {total_viagens} viagens salvas."
                )
            elif repetir_viagem and not manter_carona_base:
                messages.warning(request, "Nenhuma data foi selecionada para repetir a viagem.")
            else:
                messages.success(request, "Carona criada com sucesso.")
            if (
                not PushSubscription.objects.filter(user=request.user).exists()
                and not request.session.get("push_prompt_opt_out", False)
            ):
                request.session["ask_push_permission"] = True
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
            "datas_repeticao_post": datas_repeticao_post,
        }
    )


@login_required
def editar_carona(request, carona_id):
    carona = get_object_or_404(Carona, id=carona_id)
    vagas_ocupadas_aceitas = carona.solicitacoes.filter(
        status="aceita",
        tipo="carona",
    ).aggregate(total=Sum("quantidade"))["total"] or 0

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
            instance=carona,
            user=request.user,
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
        form = CaronaForm(instance=carona, user=request.user)

    veiculo_form = VeiculoForm()

    return render(
        request,
        "viagens/editar_carona.html",
        {
            "form": form,
            "carona": carona,
            "veiculo_form": veiculo_form,
            "vagas_ocupadas_aceitas": vagas_ocupadas_aceitas,
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

    vagas_ocupadas = carona.solicitacoes.filter(status="aceita", tipo="carona").aggregate(
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
            form.instance.tipo = "carona"

            if not request.user.is_authenticated:
                form.instance.uuid_local = uuid_local
            solicitacao = form.save()
            print(
                "DEBUG SOLICITAÇÃO:",
                solicitacao.id,
                solicitacao.uuid_local,
                solicitacao.solicitante
            )

            Notificacao.objects.create(
                usuario=carona.motorista,
                tipo="solicitacao_recebida",
                titulo="Nova solicitacao de carona",
                mensagem=f"{solicitacao.nome_solicitante} solicitou {solicitacao.quantidade} vaga(s).",
                carona=carona,
                solicitacao=solicitacao,
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
            

            # 👤 USUÁRIO LOGADO
            messages.success(
                request,
                "Solicitação enviada com sucesso! Aguarde o motorista aceitar 🚗✨"
            )
            if (
                not PushSubscription.objects.filter(user=request.user).exists()
                and not request.session.get("push_prompt_opt_out", False)
            ):
                request.session["ask_push_permission"] = True
            return redirect("lista_caronas")

    else:
        if request.user.is_authenticated:
            ultima = (
                Solicitacao.objects
                .filter(solicitante=request.user, tipo="carona")
                .order_by("-data_solicitacao")
                .first()
            )
            form = SolicitacaoForm(initial={
                "nome_solicitante": request.user.nome_completo or request.user.email,
                "telefone_solicitante": request.user.telefone,
                "endereco_solicitante": getattr(ultima, "endereco_solicitante", "") or "",
                "endereco_destino_solicitante": getattr(ultima, "endereco_destino_solicitante", "") or "",
            })
        else:
            form = SolicitacaoForm()

    return render(request, "viagens/solicitar_vaga.html", {
        "form": form,
        "carona": carona,
        "vagas_restantes": vagas_restantes
    })



def solicitar_encomenda(request, carona_id):
    carona = get_object_or_404(Carona, id=carona_id)

    if request.method == "POST":
        form = EncomendaForm(request.POST, request.FILES)

        if form.is_valid():
            if request.user.is_authenticated:
                form.instance.solicitante = request.user

            uuid_local = request.POST.get("uuid_local")

            form.instance.carona = carona
            form.instance.status = "pendente"
            form.instance.tipo = "encomenda"
            form.instance.quantidade = 1
            form.instance.malas = 0

            if not request.user.is_authenticated:
                form.instance.uuid_local = uuid_local

            solicitacao = form.save()

            Notificacao.objects.create(
                usuario=carona.motorista,
                tipo="solicitacao_recebida",
                titulo="Nova solicitacao de encomenda",
                mensagem=f"{solicitacao.nome_solicitante} solicitou envio de encomenda.",
                carona=carona,
                solicitacao=solicitacao,
            )

            if not request.user.is_authenticated:
                return render(request, "viagens/solicitacao_salva_local.html", {
                    "carona": carona,
                    "solicitacao": solicitacao,
                    "solicitacao_id": solicitacao.id,
                    "quantidade": solicitacao.quantidade,
                    "status": solicitacao.status,
                })

            telefone_motorista = (carona.motorista.telefone or "").strip()
            telefone_digitos = "".join(ch for ch in telefone_motorista if ch.isdigit())
            if telefone_digitos and len(telefone_digitos) in (10, 11):
                telefone_digitos = f"55{telefone_digitos}"

            if telefone_digitos:
                messages.success(
                    request,
                    format_html(
                        "Solicitacao de encomenda enviada com sucesso!<br>"
                        "Combine com o motorista o valor da entrega: "
                        "<a href='https://wa.me/{0}' target='_blank' rel='noopener' class='text-decoration-none'>"
                        "<i class='bi bi-whatsapp me-1'></i>{1}</a>",
                        telefone_digitos,
                        telefone_motorista or telefone_digitos,
                    )
                )
            else:
                messages.success(
                    request,
                    "Solicitacao de encomenda enviada com sucesso! Aguarde o motorista confirmar."
                )
            if (
                not PushSubscription.objects.filter(user=request.user).exists()
                and not request.session.get("push_prompt_opt_out", False)
            ):
                request.session["ask_push_permission"] = True
            return redirect("lista_caronas")
    else:
        if request.user.is_authenticated:
            ultima = (
                Solicitacao.objects
                .filter(solicitante=request.user, tipo="encomenda")
                .order_by("-data_solicitacao")
                .first()
            )
            form = EncomendaForm(initial={
                "nome_solicitante": request.user.nome_completo or request.user.email,
                "telefone_solicitante": request.user.telefone,
                "endereco_solicitante": getattr(ultima, "endereco_solicitante", "") or "",
                "endereco_destino_solicitante": getattr(ultima, "endereco_destino_solicitante", "") or "",
            })
        else:
            form = EncomendaForm()

    return render(request, "viagens/solicitar_encomenda.html", {
        "form": form,
        "carona": carona,
    })
@login_required
def aceitar_solicitacao(request, solicitacao_id):
    solicitacao = get_object_or_404(Solicitacao, id=solicitacao_id)

    if solicitacao.carona.motorista != request.user:
        return redirect("lista_caronas")

    if solicitacao.status == "aceita":
        messages.info(request, "Essa solicitacao ja foi aceita.")
        return redirect("gerenciar_solicitacoes")

    if solicitacao.tipo == "carona":
        vagas_ocupadas = solicitacao.carona.solicitacoes.filter(
            status="aceita",
            tipo="carona"
        ).aggregate(total=Sum("quantidade"))["total"] or 0

        vagas_restantes = solicitacao.carona.vagas - vagas_ocupadas

        if solicitacao.quantidade > vagas_restantes:
            messages.error(request, f"So restam {vagas_restantes} vaga(s)!")
            return redirect("gerenciar_solicitacoes")

    solicitacao.status = "aceita"
    solicitacao.save()

    if solicitacao.solicitante:
        Notificacao.objects.create(
            usuario=solicitacao.solicitante,
            tipo="viagem_aceita",
            titulo=(
                "Encomenda confirmada"
                if solicitacao.tipo == "encomenda"
                else "Viagem confirmada"
            ),
            mensagem=(
                f"Sua encomenda para {solicitacao.carona.destino} foi confirmada."
                if solicitacao.tipo == "encomenda"
                else f"Sua viagem {solicitacao.carona.origem} -> {solicitacao.carona.destino} foi confirmada."
            ),
            carona=solicitacao.carona,
            solicitacao=solicitacao,
        )

    messages.success(
        request,
        "Solicitacao aceita com sucesso!"
        if solicitacao.tipo == "carona"
        else "Encomenda aceita com sucesso!"
    )

    return redirect("gerenciar_solicitacoes")



@login_required
def gerenciar_solicitacoes(request):
    Notificacao.objects.filter(
        usuario=request.user,
        tipo="solicitacao_recebida",
        lida=False,
        solicitacao__tipo="carona",
    ).update(lida=True)

    solicitacoes = Solicitacao.objects.select_related("carona", "solicitante").filter(
        carona__motorista=request.user,
        status='pendente'
    ).order_by('-data_solicitacao')

    carona_ids = list({s.carona_id for s in solicitacoes})
    vagas_ocupadas_map = {
        item["carona_id"]: (item["total"] or 0)
        for item in (
            Solicitacao.objects.filter(
                carona_id__in=carona_ids,
                tipo="carona",
                status="aceita",
            )
            .values("carona_id")
            .annotate(total=Sum("quantidade"))
        )
    }
    encomendas_confirmadas_map = {
        item["carona_id"]: item["total"]
        for item in (
            Solicitacao.objects.filter(
                carona_id__in=carona_ids,
                tipo="encomenda",
                status="aceita",
            )
            .values("carona_id")
            .annotate(total=Count("id"))
        )
    }

    for s in solicitacoes:
        ocupadas = vagas_ocupadas_map.get(s.carona_id, 0)
        s.vagas_restantes_carona = max((s.carona.vagas or 0) - ocupadas, 0)
        s.encomendas_confirmadas_carona = encomendas_confirmadas_map.get(s.carona_id, 0)
    
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
            titulo="Solicitacao recusada",
            mensagem=(
                "O motorista recusou sua solicitacao de encomenda."
                if solicitacao.tipo == "encomenda"
                else "O motorista recusou sua solicitacao de carona."
            ),
            carona=solicitacao.carona,
            solicitacao=solicitacao,
        )

    messages.success(
        request,
        "Solicitacao recusada!"
        if solicitacao.tipo == "carona"
        else "Encomenda recusada!"
    )
    return redirect("gerenciar_solicitacoes")


def minhas_solicitacoes(request):

    if request.user.is_authenticated:

        Notificacao.objects.filter(
            usuario=request.user,
            tipo__in=["solicitacao_recusada"],
            lida=False
        ).update(lida=True)
        
        minhas = Solicitacao.objects.filter(
            solicitante=request.user,
            tipo="carona",
        ).order_by('carona__data', 'carona__hora', '-data_solicitacao')

        return render(request, 'viagens/minhas_solicitacoes.html', {
            'solicitacoes': minhas,
            'modo': 'bd'
        })

    return render(request, 'viagens/minhas_solicitacoes.html', {
        'solicitacoes': [],
        'modo': 'local'
    })


def minhas_encomendas_passageiro(request):
    if request.user.is_authenticated:
        Notificacao.objects.filter(
            usuario=request.user,
            tipo__in=["viagem_aceita", "solicitacao_recusada", "viagem_cancelada", "viagem_concluida"],
            lida=False,
            solicitacao__tipo="encomenda",
        ).update(lida=True)

        mostrar_todas = request.GET.get("todas") == "1"
        limite_recentes = 6
        itens_por_pagina = 12

        encomendas_qs = (
            Solicitacao.objects
            .filter(solicitante=request.user, tipo="encomenda")
            .select_related("carona", "solicitante", "carona__motorista")
            .order_by("carona__data", "carona__hora", "-data_solicitacao")
        )
        page_obj = None
        encomendas = encomendas_qs
        if mostrar_todas:
            paginator = Paginator(encomendas_qs, itens_por_pagina)
            page_obj = paginator.get_page(request.GET.get("page"))
            encomendas = page_obj.object_list

        viagens_ativas = (
            Carona.objects
            .filter(
                status="ativa",
                solicitacoes__solicitante=request.user,
                solicitacoes__tipo="encomenda",
                solicitacoes__status="aceita",
            )
            .annotate(
                encomendas_ativas=Count(
                    "solicitacoes",
                    filter=Q(
                        solicitacoes__solicitante=request.user,
                        solicitacoes__tipo="encomenda",
                        solicitacoes__status="aceita",
                    ),
                ),
                encomendas_pendentes=Count(
                    "solicitacoes",
                    filter=Q(
                        solicitacoes__solicitante=request.user,
                        solicitacoes__tipo="encomenda",
                        solicitacoes__status="pendente",
                    ),
                ),
                ultima_encomenda=Max(
                    "solicitacoes__data_solicitacao",
                    filter=Q(
                        solicitacoes__solicitante=request.user,
                        solicitacoes__tipo="encomenda",
                    ),
                ),
            )
            .order_by("data", "hora")
        )

        return render(request, "viagens/minhas_encomendas_passageiro.html", {
            "encomendas": encomendas,
            "viagens_ativas": viagens_ativas,
            "encomendas_recentes": encomendas_qs.order_by("-data_solicitacao")[:limite_recentes],
            "mostrar_todas": mostrar_todas,
            "page_obj": page_obj,
            "modo": "bd",
        })

    return render(request, "viagens/minhas_encomendas_passageiro.html", {
        "encomendas": [],
        "modo": "local",
    })


@login_required
def minhas_encomendas_carona_passageiro(request, carona_id):
    carona = get_object_or_404(Carona, id=carona_id)
    encomendas = (
        Solicitacao.objects
        .filter(
            carona=carona,
            solicitante=request.user,
            tipo="encomenda",
            status__in=["pendente", "aceita"],
        )
        .select_related("solicitante", "carona", "carona__motorista")
        .order_by("carona__data", "carona__hora", "-data_solicitacao")
    )

    if not encomendas.exists():
        messages.warning(request, "Voce nao possui encomendas nessa viagem.")
        return redirect("minhas_encomendas_passageiro")

    return render(request, "viagens/minhas_encomendas_carona_passageiro.html", {
        "carona": carona,
        "encomendas": encomendas,
    })


def minhas_encomendas_carona_publica(request, carona_id):
    return render(request, "viagens/minhas_encomendas_carona_publica.html", {
        "carona_id": carona_id,
    })



def minhas_viagens(request):

    if request.user.is_authenticated:

        Notificacao.objects.filter(
            usuario=request.user,
            tipo__in=["viagem_atualizada", "viagem_aceita", "viagem_cancelada", "viagem_concluida"],
            solicitacao__tipo="carona",
            lida=False
        ).update(lida=True)

        viagens_base = Solicitacao.objects.filter(
            solicitante=request.user,
            tipo='carona',
            status='aceita',
        ).select_related('carona', 'carona__motorista')
        viagens_ativas = viagens_base.filter(
            carona__status='ativa'
        ).order_by('carona__data', 'carona__hora', '-data_solicitacao')
        viagens_recentes = viagens_base.order_by("-data_solicitacao")[:6]


        return render(request, 'viagens/minhas_viagens.html', {
            'viagens_ativas': viagens_ativas,
            'viagens_recentes': viagens_recentes,
            'modo': 'bd'
        })

    return render(request, 'viagens/minhas_viagens.html', {
        'viagens': [],
        'modo': 'local'
    })


@login_required
@require_POST
def cancelar_solicitacao(request, id):
    s = get_object_or_404(
        Solicitacao,
        id=id,
        solicitante=request.user
    )

    if s.carona.status != "ativa":
        messages.warning(request, "Esta viagem ja foi concluida e nao pode ser cancelada.")
        destino = (
            "minhas_encomendas_passageiro"
            if s.tipo == "encomenda"
            else "minhas_viagens"
        )
        return redirect(destino)

    with transaction.atomic():
        # Encomenda pendente cancelada pelo passageiro nao deve ficar no banco.
        if s.tipo == "encomenda" and s.status == "pendente":
            s.delete()
            return redirect("minhas_encomendas_passageiro")

        if s.status == "pendente":
            destino = (
                "minhas_encomendas_passageiro"
                if s.tipo == "encomenda"
                else "minhas_solicitacoes"
            )
            s.delete()
            return redirect(destino)

        if s.status == "aceita":
            s.mudar_status("cancelada")
            destino = (
                "minhas_encomendas_passageiro"
                if s.tipo == "encomenda"
                else "minhas_viagens"
            )
            return redirect(destino)

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

    if solicitacao.carona.status != "ativa":
        return HttpResponseBadRequest("Carona nao esta ativa")

    with transaction.atomic():
        # Para visitante, encomenda pendente cancelada tambem e removida do banco.
        if solicitacao.tipo == "encomenda" and solicitacao.status == "pendente":
            solicitacao.delete()
            return HttpResponse(status=204)

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
        {"veiculos": veiculos, "veiculo_form": VeiculoForm()}
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
            messages.success(request, "Veiculo atualizado com sucesso.")
            return redirect("meus_veiculos")

        messages.error(request, "Erro ao atualizar veiculo.")
        veiculos = Veiculo.objects.filter(motorista=request.user)
        return render(
            request,
            "viagens/meus_veiculos.html",
            {
                "veiculos": veiculos,
                "veiculo_form": VeiculoForm(),
                "invalid_edit_veiculo_id": veiculo.id,
                "invalid_edit_data": request.POST,
                "invalid_edit_errors": form.errors,
            },
        )

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

    if carona.status == "concluida":
        return redirect("lista_caronas")

    carona.status = "concluida"
    carona.save(update_fields=["status"])

    solicitacoes_aceitas = (
        carona.solicitacoes
        .select_related("solicitante")
        .filter(status="aceita")
    )

    for s in solicitacoes_aceitas:
        if not s.solicitante:
            continue

        if s.tipo == "encomenda":
            titulo = "Encomenda concluida"
            mensagem = f"A entrega da sua encomenda para {carona.destino} foi concluida."
        else:
            titulo = "Viagem concluida"
            mensagem = f"Sua viagem de {carona.origem} para {carona.destino} foi concluida."

        Notificacao.objects.create(
            usuario=s.solicitante,
            tipo="viagem_concluida",
            titulo=titulo,
            mensagem=mensagem,
            carona=carona,
            solicitacao=s,
        )

    return redirect('lista_caronas')


def historico_viagens(request):
    tipo = request.GET.get('tipo', 'todas')
    data_inicial_raw = (request.GET.get("data_inicial") or "").strip()
    data_final_raw = (request.GET.get("data_final") or "").strip()
    data_inicial = parse_date(data_inicial_raw) if data_inicial_raw else None
    data_final = parse_date(data_final_raw) if data_final_raw else None
    if data_inicial and data_final and data_inicial > data_final:
        data_inicial, data_final = data_final, data_inicial

    filtro_data_carona = Q()
    if data_inicial:
        filtro_data_carona &= Q(data__gte=data_inicial)
    if data_final:
        filtro_data_carona &= Q(data__lte=data_final)

    filtro_data_encomenda = Q()
    if data_inicial:
        filtro_data_encomenda &= Q(carona__data__gte=data_inicial)
    if data_final:
        filtro_data_encomenda &= Q(carona__data__lte=data_final)

    filtro_data_qs = ""
    if data_inicial:
        filtro_data_qs += f"&data_inicial={data_inicial.isoformat()}"
    if data_final:
        filtro_data_qs += f"&data_final={data_final.isoformat()}"

    caronas = Carona.objects.none()
    historico_itens = []
    solicitacoes = None

    if request.user.is_authenticated:
        base_filter = Q(status='concluida') & filtro_data_carona

        if tipo == 'motorista':
            filtro = base_filter & Q(motorista=request.user)
        elif tipo == 'passageiro':
            filtro = base_filter & Q(
                solicitacoes__solicitante=request.user,
                solicitacoes__status='aceita',
                solicitacoes__tipo='carona'
            )
        elif tipo == 'encomenda':
            filtro = Q(pk__in=[])
        else:
            filtro = base_filter & (
                Q(motorista=request.user) |
                Q(
                    solicitacoes__solicitante=request.user,
                    solicitacoes__status='aceita',
                    solicitacoes__tipo='carona'
                )
            )

        caronas = (
            Carona.objects
            .filter(filtro)
            .distinct()
            .order_by('-data', '-hora')
        )

        for carona in caronas:
            historico_itens.append({
                'categoria': 'carona',
                'carona': carona,
                'descricao_item': '',
                'foto_encomenda': None,
                'papel': 'motorista' if carona.motorista_id == request.user.id else 'passageiro',
            })

        if tipo in ['todas', 'encomenda']:
            encomendas = (
                Solicitacao.objects
                .select_related('carona', 'solicitante')
                .filter(
                    tipo='encomenda',
                    status='aceita',
                    carona__status='concluida',
                )
                .filter(
                    Q(carona__motorista=request.user) |
                    Q(solicitante=request.user)
                )
                .filter(filtro_data_encomenda)
                .distinct()
                .order_by('-carona__data', '-carona__hora', '-data_solicitacao')
            )

            for e in encomendas:
                historico_itens.append({
                    'categoria': 'encomenda',
                    'carona': e.carona,
                    'descricao_item': e.descricao_item or '',
                    'foto_encomenda': e.foto_encomenda,
                    'papel': 'motorista' if e.carona.motorista_id == request.user.id else 'passageiro',
                })

        historico_itens.sort(
            key=lambda item: (item['carona'].data, item['carona'].hora),
            reverse=True
        )

    else:
        uuid_local = request.GET.get('uuid')

        if uuid_local:
            solicitacoes = (
                Solicitacao.objects
                .select_related('carona')
                .filter(uuid_local=uuid_local)
                .order_by('-data_solicitacao')
            )

    return render(request, 'viagens/historico.html', {
        'caronas': caronas,
        'historico_itens': historico_itens,
        'solicitacoes': solicitacoes,
        'tipo': tipo,
        "data_inicial": data_inicial.isoformat() if data_inicial else "",
        "data_final": data_final.isoformat() if data_final else "",
        "filtro_data_qs": filtro_data_qs,
    })


def termos_uso(request):
    return render(request, "viagens/termos_uso.html")


def politica_privacidade(request):
    return render(request, "viagens/politica_privacidade.html")

def api_estado_caronas(request):
    ids = request.GET.get("ids", "")
    result = []

    if ids:
        carona_ids = [i for i in ids.split(",") if i.isdigit()]
        caronas = Carona.objects.filter(id__in=carona_ids)

        vagas_ocupadas_map = {
            item["carona_id"]: (item["total"] or 0)
            for item in (
                Solicitacao.objects.filter(
                    carona_id__in=carona_ids,
                    tipo="carona",
                    status="aceita",
                )
                .values("carona_id")
                .annotate(total=Sum("quantidade"))
            )
        }
        passageiros_confirmados_map = {
            item["carona_id"]: (item["total"] or 0)
            for item in (
                Solicitacao.objects.filter(
                    carona_id__in=carona_ids,
                    tipo="carona",
                    status="aceita",
                )
                .values("carona_id")
                .annotate(total=Sum("quantidade"))
            )
        }
        encomendas_confirmadas_map = {
            item["carona_id"]: item["total"]
            for item in (
                Solicitacao.objects.filter(
                    carona_id__in=carona_ids,
                    tipo="encomenda",
                    status="aceita",
                )
                .values("carona_id")
                .annotate(total=Count("id"))
            )
        }

        for c in caronas:
            ocupadas = vagas_ocupadas_map.get(c.id, 0)
            result.append({
                "id": c.id,
                "origem": c.origem,
                "destino": c.destino,
                "data": c.data.strftime("%Y-%m-%d"),
                "hora": c.hora.strftime("%H:%M"),
                "motorista_nome": c.motorista.nome_curto or c.motorista.nome_completo,
                "status": c.status,
                "vagas_restantes": max((c.vagas or 0) - ocupadas, 0),
                "passageiros_confirmados": passageiros_confirmados_map.get(c.id, 0),
                "encomendas_confirmadas": encomendas_confirmadas_map.get(c.id, 0),
            })

    return JsonResponse({ "result": result })

@login_required
def minhas_caronas_view(request):
    Notificacao.objects.filter(
        usuario=request.user,
        tipo="passageiro_cancelou",
        solicitacao__tipo="carona",
        lida=False
    ).update(lida=True)

    Notificacao.objects.filter(
        usuario=request.user,
        tipo="viagem_concluida",
        lida=False
    ).update(lida=True)

    caronas = (
        Carona.objects
        .filter(
            motorista=request.user,
            status='ativa' 
        )
        .order_by('data', 'hora', '-criado_em')
    )

    for carona in caronas:
        carona.passageiros_aceitos = carona.solicitacoes.filter(status='aceita', tipo='carona')
        carona.passageiros_pendentes = carona.solicitacoes.filter(
            status="pendente",
            tipo="carona",
        ).select_related("solicitante")
        carona.encomendas_ativas_lista = carona.solicitacoes.filter(
            tipo="encomenda",
            status__in=["pendente", "aceita"]
        ).select_related("solicitante")
        carona.encomendas_para_entregar = carona.solicitacoes.filter(
            tipo="encomenda",
            status="aceita"
        ).count()
        carona.encomendas_pendentes = carona.solicitacoes.filter(
            tipo='encomenda',
            status='pendente'
        ).count()
        carona.encomendas_ativas = carona.solicitacoes.filter(
            tipo='encomenda',
            status='aceita'
        ).count()
        passageiros_confirmados_total = carona.passageiros_aceitos.aggregate(total=Sum("quantidade"))["total"] or 0
        carona.passageiros_confirmados = passageiros_confirmados_total
        carona.vagas_restantes = max((carona.vagas or 0) - passageiros_confirmados_total, 0)

    caronas_recentes = (
        Carona.objects
        .filter(motorista=request.user)
        .exclude(status="ativa")
        .order_by("-data", "-hora", "-criado_em")[:6]
    )

    return render(request, "viagens/minhas_caronas.html", {
        "caronas": caronas,
        "caronas_recentes": caronas_recentes,
    })


@login_required
def encomendas_carona(request, carona_id):
    carona = get_object_or_404(Carona, id=carona_id, motorista=request.user)
    Notificacao.objects.filter(
        usuario=request.user,
        tipo="solicitacao_recebida",
        lida=False,
        solicitacao__tipo="encomenda",
        carona=carona,
    ).update(lida=True)

    encomendas = Solicitacao.objects.filter(
        carona=carona,
        tipo="encomenda",
        status__in=["pendente", "aceita"],
    )

    encomendas = encomendas.select_related("solicitante", "carona").order_by("carona__data", "carona__hora", "-data_solicitacao")

    return render(request, "viagens/encomendas_carona.html", {
        "carona": carona,
        "encomendas": encomendas,
    })


@login_required
def detalhe_encomenda(request, encomenda_id):
    encomenda = get_object_or_404(
        Solicitacao.objects.select_related("carona", "solicitante", "carona__motorista"),
        id=encomenda_id,
        tipo="encomenda",
    )

    pode_visualizar = (
        encomenda.carona.motorista_id == request.user.id
        or encomenda.solicitante_id == request.user.id
    )
    if not pode_visualizar:
        return HttpResponseForbidden("Voce nao tem permissao para visualizar esta encomenda.")

    return render(request, "viagens/detalhe_encomenda.html", {
        "encomenda": encomenda,
    })


@login_required
def passageiros_carona(request, carona_id):
    carona = get_object_or_404(Carona, id=carona_id, motorista=request.user)
    passageiros_pendentes = (
        Solicitacao.objects
        .filter(carona=carona, tipo="carona", status="pendente")
        .select_related("solicitante")
        .order_by("-data_solicitacao")
    )
    passageiros_aceitos = (
        Solicitacao.objects
        .filter(carona=carona, tipo="carona", status="aceita")
        .select_related("solicitante")
        .order_by("-data_solicitacao")
    )
    return render(request, "viagens/passageiros_carona.html", {
        "carona": carona,
        "passageiros_pendentes": passageiros_pendentes,
        "passageiros_aceitos": passageiros_aceitos,
    })


@login_required
def minhas_encomendas(request):
    Notificacao.objects.filter(
        usuario=request.user,
        tipo="passageiro_cancelou",
        solicitacao__tipo="encomenda",
        lida=False
    ).update(lida=True)

    mostrar_todas = request.GET.get("todas") == "1"
    limite_recentes = 6
    itens_por_pagina = 12

    encomendas_qs = (
        Solicitacao.objects
        .filter(carona__motorista=request.user, tipo="encomenda")
        .select_related("solicitante", "carona")
        .order_by("carona__data", "carona__hora", "-data_solicitacao")
    )
    page_obj = None
    encomendas = encomendas_qs
    if mostrar_todas:
        paginator = Paginator(encomendas_qs, itens_por_pagina)
        page_obj = paginator.get_page(request.GET.get("page"))
        encomendas = page_obj.object_list

    viagens_ativas = (
        Carona.objects
        .filter(
            motorista=request.user,
            status="ativa",
            solicitacoes__tipo="encomenda",
        )
        .annotate(
            encomendas_ativas=Count(
                "solicitacoes",
                filter=Q(solicitacoes__tipo="encomenda", solicitacoes__status="aceita")
            ),
            encomendas_pendentes=Count(
                "solicitacoes",
                filter=Q(solicitacoes__tipo="encomenda", solicitacoes__status="pendente")
            ),
            ultima_encomenda=Max(
                "solicitacoes__data_solicitacao",
                filter=Q(solicitacoes__tipo="encomenda")
            ),
        )
        .order_by("data", "hora")
    )

    return render(request, "viagens/minhas_encomendas.html", {
        "encomendas": encomendas,
        "viagens_ativas": viagens_ativas,
        "encomendas_recentes": encomendas_qs.order_by("-data_solicitacao")[:limite_recentes],
        "mostrar_todas": mostrar_todas,
        "page_obj": page_obj,
    })

@login_required
@require_POST
def remover_passageiro(request, pk):
    solicitacao = get_object_or_404(Solicitacao, pk=pk)

    if solicitacao.carona.motorista != request.user or solicitacao.tipo != "carona":
        return redirect("lista_caronas")

    if solicitacao.status not in ["aceita", "pendente"]:
        messages.warning(request, "Esse passageiro nao pode mais ser removido.")
        return redirect(request.META.get("HTTP_REFERER", "minhas_caronas"))

    solicitacao.status = "cancelada"
    solicitacao.save(update_fields=["status"])

    if solicitacao.solicitante:
        Notificacao.objects.create(
            usuario=solicitacao.solicitante,
            tipo="viagem_cancelada",
            titulo="Viagem cancelada pelo motorista",
            mensagem="O motorista cancelou sua participacao nessa carona.",
            carona=solicitacao.carona,
            solicitacao=solicitacao,
        )

    messages.success(request, "Passageiro removido com sucesso.")
    return redirect(request.META.get("HTTP_REFERER", "minhas_caronas"))


@login_required
@require_POST
def cancelar_encomenda_motorista(request, pk):
    solicitacao = get_object_or_404(Solicitacao, pk=pk)

    if solicitacao.carona.motorista != request.user or solicitacao.tipo != "encomenda":
        return redirect("lista_caronas")

    if solicitacao.carona.status != "ativa":
        messages.warning(request, "Essa viagem ja foi concluida e a encomenda nao pode ser cancelada.")
        return redirect(request.META.get("HTTP_REFERER", "minhas_encomendas"))

    if solicitacao.status not in ["aceita", "pendente"]:
        messages.warning(request, "Essa encomenda nao pode mais ser cancelada.")
        return redirect(request.META.get("HTTP_REFERER", "minhas_encomendas"))

    solicitacao.status = "cancelada"
    solicitacao.save(update_fields=["status"])

    if solicitacao.solicitante:
        Notificacao.objects.create(
            usuario=solicitacao.solicitante,
            tipo="viagem_cancelada",
            titulo="Entrega cancelada pelo motorista",
            mensagem="O motorista cancelou a entrega da sua encomenda.",
            carona=solicitacao.carona,
            solicitacao=solicitacao,
        )

    messages.success(request, "Encomenda cancelada com sucesso.")
    return redirect(request.META.get("HTTP_REFERER", "minhas_encomendas"))

@login_required
def marcar_notificacoes_como_lidas(request):
    Notificacao.objects.filter(
        usuario=request.user,
        lida=False
    ).update(lida=True)

    return JsonResponse({"status": "ok"})


@login_required
@require_POST
def limpar_notificacoes(request):
    Notificacao.objects.filter(usuario=request.user).delete()
    return JsonResponse({"status": "ok"})





