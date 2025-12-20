from viagens.models import Solicitacao

def notificacoes_solicitacoes(request):
    if not request.user.is_authenticated:
        return {
            "qtd_solicitacoes_pendentes": 0,
            "qtd_solicitacoes_novas": 0,
            "qtd_viagens_novas": 0,
            "qtd_notificacoes_passageiro": 0,
        }

    # 🚗 MOTORISTA
    qtd_solicitacoes_pendentes = Solicitacao.objects.filter(
        carona__motorista=request.user,
        status="pendente"
    ).count()

    # 👤 PASSAGEIRO — respostas novas
    qtd_solicitacoes_novas = Solicitacao.objects.filter(
        solicitante=request.user,
        visto_passageiro=False
    ).exclude(status="pendente").count()

    # ✈️ PASSAGEIRO — viagens novas
    qtd_viagens_novas = Solicitacao.objects.filter(
        solicitante=request.user,
        status="aceita",
        visto_viagem=False
    ).count()

    # 🔔 TOTAL DO PASSAGEIRO
    qtd_notificacoes_passageiro = (
        qtd_solicitacoes_novas + qtd_viagens_novas
    )

    return {
        "qtd_solicitacoes_pendentes": qtd_solicitacoes_pendentes,
        "qtd_solicitacoes_novas": qtd_solicitacoes_novas,
        "qtd_viagens_novas": qtd_viagens_novas,
        "qtd_notificacoes_passageiro": qtd_notificacoes_passageiro,
    }
