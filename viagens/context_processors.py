from viagens.models import Notificacao, Solicitacao


def notificacoes(request):
    if not request.user.is_authenticated:
        return {
            "qtd_solicitacoes_pendentes": 0,
            "qtd_solicitacoes_novas": 0,
            "qtd_viagens_novas": 0,
            "qtd_encomendas_novas": 0,
            "qtd_notificacoes_passageiro": 0,
        }

    qtd_solicitacoes_pendentes = Solicitacao.objects.filter(
        carona__motorista=request.user,
        status="pendente",
    ).count()

    qtd_eventos_motorista_caronas = Notificacao.objects.filter(
        usuario=request.user,
        tipo="passageiro_cancelou",
        solicitacao__tipo="carona",
        lida=False,
    ).count()

    qtd_eventos_motorista_encomendas = Notificacao.objects.filter(
        usuario=request.user,
        tipo="passageiro_cancelou",
        solicitacao__tipo="encomenda",
        lida=False,
    ).count()

    qtd_eventos_motorista_conclusao = Notificacao.objects.filter(
        usuario=request.user,
        tipo="viagem_concluida",
        lida=False,
    ).count()

    qtd_solicitacoes_novas = Notificacao.objects.filter(
        usuario=request.user,
        tipo__in=["solicitacao_aceita", "solicitacao_recusada"],
        solicitacao__tipo="carona",
        lida=False,
    ).count()

    qtd_viagens_novas = Notificacao.objects.filter(
        usuario=request.user,
        tipo__in=["viagem_atualizada", "viagem_aceita", "viagem_cancelada", "viagem_concluida"],
        solicitacao__tipo="carona",
        lida=False,
    ).count()

    qtd_encomendas_novas = Notificacao.objects.filter(
        usuario=request.user,
        tipo__in=["viagem_aceita", "solicitacao_recusada", "viagem_cancelada"],
        solicitacao__tipo="encomenda",
        lida=False,
    ).count()

    qtd_notificacoes_passageiro = (
        qtd_solicitacoes_novas + qtd_viagens_novas + qtd_encomendas_novas
    )
    qtd_eventos_motorista = qtd_eventos_motorista_caronas + qtd_eventos_motorista_conclusao
    qtd_notificacoes_motorista = (
        qtd_solicitacoes_pendentes
        + qtd_eventos_motorista
        + qtd_eventos_motorista_encomendas
    )

    return {
        "qtd_solicitacoes_pendentes": qtd_solicitacoes_pendentes,
        "qtd_eventos_motorista": qtd_eventos_motorista,
        "qtd_eventos_motorista_encomendas": qtd_eventos_motorista_encomendas,
        "qtd_notificacoes_motorista": qtd_notificacoes_motorista,
        "qtd_solicitacoes_novas": qtd_solicitacoes_novas,
        "qtd_viagens_novas": qtd_viagens_novas,
        "qtd_encomendas_novas": qtd_encomendas_novas,
        "qtd_notificacoes_passageiro": qtd_notificacoes_passageiro,
    }
