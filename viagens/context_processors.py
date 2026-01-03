from viagens.models import Notificacao, Solicitacao

def notificacoes(request):

    if not request.user.is_authenticated:
        return {
            "qtd_solicitacoes_pendentes": 0,
            "qtd_solicitacoes_novas": 0,
            "qtd_viagens_novas": 0,
            "qtd_notificacoes_passageiro": 0,
        }

    # 🚗 MOTORISTA — pendências reais (ação necessária)
    qtd_solicitacoes_pendentes = Solicitacao.objects.filter(
        carona__motorista=request.user,
        status="pendente"
    ).count()

    # 🚗 MOTORISTA — eventos (informativos)
    qtd_eventos_motorista = Notificacao.objects.filter(
        usuario=request.user,
        tipo__in=[
            "passageiro_cancelou", 
            "viagem_concluida",  
        ],
        lida=False
    ).count()

    # 👤 PASSAGEIRO — respostas de solicitações
    qtd_solicitacoes_novas = Notificacao.objects.filter(
        usuario=request.user,
        tipo__in=["solicitacao_aceita", "solicitacao_recusada"],
        lida=False
    ).count()

    # ✈️ PASSAGEIRO — eventos de viagem
    qtd_viagens_novas = Notificacao.objects.filter(
        usuario=request.user,
        tipo__in=[
            "viagem_atualizada",
            "viagem_aceita",
            "viagem_cancelada",
            "viagem_concluida"
        ],
        lida=False
    ).count()


    qtd_notificacoes_passageiro = (
        qtd_solicitacoes_novas + qtd_viagens_novas
    )

    qtd_notificacoes_motorista = (
    qtd_solicitacoes_pendentes + qtd_eventos_motorista
    )

    return {
    # MOTORISTA
    "qtd_solicitacoes_pendentes": qtd_solicitacoes_pendentes,
    "qtd_eventos_motorista": qtd_eventos_motorista,
    "qtd_notificacoes_motorista": qtd_notificacoes_motorista,

    # PASSAGEIRO
    "qtd_solicitacoes_novas": qtd_solicitacoes_novas,
    "qtd_viagens_novas": qtd_viagens_novas,
    "qtd_notificacoes_passageiro": qtd_notificacoes_passageiro,
    }
