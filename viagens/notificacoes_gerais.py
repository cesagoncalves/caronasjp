from viagens.models import Notificacao

def notificacoes_gerais(request):
    if not request.user.is_authenticated:
        return {}

    notificacoes_qs = Notificacao.objects.filter(
        usuario=request.user
    ).order_by("-criada_em")

    return {
        "qtd_notificacoes_gerais": notificacoes_qs.filter(lida=False).count(),
        "notificacoes_recentes": notificacoes_qs[:10],
    }
