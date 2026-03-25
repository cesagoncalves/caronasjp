import json

from viagens.models import Solicitacao


def parse_solicitacao_ids(valor):
    if not valor:
        return []

    bruto = str(valor).strip()
    if not bruto:
        return []

    candidatos = []
    try:
        if bruto.startswith("["):
            parsed = json.loads(bruto)
            if isinstance(parsed, list):
                candidatos = parsed
        else:
            candidatos = [p.strip() for p in bruto.split(",")]
    except Exception:
        candidatos = [p.strip() for p in bruto.split(",")]

    ids = []
    vistos = set()
    for item in candidatos:
        try:
            numero = int(str(item).strip())
        except (TypeError, ValueError):
            continue
        if numero <= 0 or numero in vistos:
            continue
        vistos.add(numero)
        ids.append(numero)
    return ids


def vincular_solicitacoes_dispositivo(
    usuario,
    *,
    migrar=False,
    uuid_local="",
    solicitacao_ids=None,
):
    if not migrar:
        return 0

    uuid_limpo = (uuid_local or "").strip()
    if not uuid_limpo:
        return 0

    qs = Solicitacao.objects.filter(
        uuid_local=uuid_limpo,
        solicitante__isnull=True,
    )

    if solicitacao_ids:
        qs = qs.filter(id__in=solicitacao_ids)

    return qs.update(solicitante=usuario)
