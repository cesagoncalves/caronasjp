console.log("notificacoes.js carregado");

async function sincronizarSolicitacoes() {
    const lista = getSolicitacoes();
    if (!lista.length) return;

    const uuidLocal = localStorage.getItem("uuid_local");
    let url = "";

    const todosComId = lista.every(s => !!s.id);

    if (!uuidLocal || todosComId) {
        const ids = lista.map(s => s.id).join(",");
        url = `/api/status-solicitacoes/?ids=${ids}`;
    } else {
        const pares = lista
            .map(s => `${s.carona_id}:${s.quantidade}`)
            .join(",");

        url = `/api/status-solicitacoes/?caronas=${pares}`;
    }

    try {
        const resp = await fetch(url);
        if (!resp.ok) return;

        const data = await resp.json();
        const backend = data.result || [];
        let alterou = false;

        lista.forEach(local => {
            const remoto = backend.find(b => String(b.id) === String(local.id));
            if (!remoto) return;

            if (local.carona_status !== remoto.carona_status) {
                local.carona_status = remoto.carona_status;
                alterou = true;
            }

            if (local.status !== remoto.status) {
                const statusAnterior = local.status;
                local.status = remoto.status;

                if (
                    statusAnterior === "pendente" &&
                    (remoto.status === "recusada" || remoto.status === "cancelada")
                ) {
                    local.visto_solicitacao = false;
                }

                if (statusAnterior === "pendente" && remoto.status === "aceita") {
                    if (local.tipo === "encomenda") {
                        local.visto_solicitacao = false;
                    } else {
                        local.visto_viagem = false;
                    }
                }

                if (
                    statusAnterior === "aceita" &&
                    (remoto.status === "cancelada" || remoto.status === "excluida")
                ) {
                    local.visto_viagem = false;
                }

                alterou = true;
                console.log("STATUS:", statusAnterior, "->", remoto.status);
            }

            if (remoto.viagem_atualizada) {
                const dataEdicaoRemota = remoto.data_edicao
                    ? new Date(remoto.data_edicao)
                    : null;

                const ultimaLeitura = local.ultima_edicao_lida
                    ? new Date(local.ultima_edicao_lida)
                    : null;

                if (
                    !ultimaLeitura ||
                    (dataEdicaoRemota && dataEdicaoRemota > ultimaLeitura)
                ) {
                    local.visto_viagem = false;
                    local.viagem_atualizada = true;
                    alterou = true;
                }
            }
        });

        if (alterou) {
            saveSolicitacoes(lista);
        }

        atualizarNavbar();
    } catch (e) {
        console.error("Erro na sincronizacao", e);
        atualizarNavbar();
    }
}

function atualizarNavbar() {
    const lista = getSolicitacoes();
    const STATUS_SOLICITACAO = ["aceita", "recusada", "cancelada"];

    const novasSolicitacoes = lista.filter(
        s =>
            s.tipo !== "encomenda" &&
            STATUS_SOLICITACAO.includes(s.status) &&
            !s.visto_solicitacao
    ).length;

    const novasEncomendas = lista.filter(
        s =>
            s.tipo === "encomenda" &&
            STATUS_SOLICITACAO.includes(s.status) &&
            !s.visto_solicitacao
    ).length;

    const novasViagens = lista.filter(
        s => s.tipo !== "encomenda" && !s.visto_viagem
    ).length;

    const contadorViagens = document.body.dataset.page === "viagens-local"
        ? 0
        : novasViagens;

    atualizarBadge("badge-solicitacoes", "nav-minhas-solicitacoes", novasSolicitacoes);
    atualizarBadge("badge-viagens", "nav-minhas-viagens", contadorViagens);
    atualizarBadge("badge-encomendas", "nav-minhas-encomendas", novasEncomendas);

    atualizarBadge("badge-solicitacoes-mobile", "nav-minhas-solicitacoes-mobile", novasSolicitacoes);
    atualizarBadge("badge-viagens-mobile", "nav-minhas-viagens-mobile", contadorViagens);
    atualizarBadge("badge-encomendas-mobile", "nav-minhas-encomendas-mobile", novasEncomendas);
}

function atualizarBadge(badgeId, linkId, qtd) {
    const badge = document.getElementById(badgeId);
    const link = document.getElementById(linkId);
    if (!badge || !link) return;

    if (qtd > 0) {
        badge.textContent = qtd;
        badge.classList.remove("d-none");
        link.classList.add("text-warning", "fw-bold");
    } else {
        badge.classList.add("d-none");
        link.classList.remove("text-warning", "fw-bold");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    sincronizarSolicitacoes();
    setInterval(sincronizarSolicitacoes, 30000);
});
