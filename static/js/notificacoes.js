console.log("🔔 notificacoes.js carregado");

async function sincronizarSolicitacoes() {
    const lista = getSolicitacoes();
    if (!lista.length) return;

    // 🔐 Detecta se é visitante (uuid_local existe)
    const uuidLocal = localStorage.getItem("uuid_local");

    let url = "";

    const todosComId = lista.every(s => !!s.id);

    if (!uuidLocal || todosComId) {
        // Usa ids quando possível (evita colisão entre carona/encomenda)
        const ids = lista.map(s => s.id).join(",");
        url = `/api/status-solicitacoes/?ids=${ids}`;
    } else {
        // Fallback antigo para registros sem id
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
            const remoto = backend.find(b =>
                String(b.id) === String(local.id)
            );
            if (!remoto) return;

            // 🔄 STATUS mudou
            if (local.status !== remoto.status) {
                const statusAnterior = local.status;
                local.status = remoto.status;

                // 🔴 SOLICITAÇÃO recusada / cancelada
                if (
                    statusAnterior === "pendente" &&
                    (remoto.status === "recusada" || remoto.status === "cancelada")
                ) {
                    local.visto_solicitacao = false;
                }

                // 🟢 VIAGEM aceita
                if (
                    statusAnterior === "pendente" &&
                    remoto.status === "aceita"
                ) {
                    local.visto_viagem = false;
                }

                // 🔴 VIAGEM cancelada / excluída
                if (
                    statusAnterior === "aceita" &&
                    (remoto.status === "cancelada" || remoto.status === "excluida")
                ) {
                    local.visto_viagem = false;
                }

                alterou = true;
                console.log("STATUS:", statusAnterior, "→", remoto.status);
            }

            // ✏️ VIAGEM EDITADA (independente do status)
            if (remoto.viagem_atualizada) {

                // ⏱ data da última edição vinda do backend
                const dataEdicaoRemota = remoto.data_edicao
                    ? new Date(remoto.data_edicao)
                    : null;

                // 👀 data da última leitura local
                const ultimaLeitura = local.ultima_edicao_lida
                    ? new Date(local.ultima_edicao_lida)
                    : null;

                // 🔔 só notifica se:
                // - nunca foi lida
                // - OU edição é mais nova que a leitura
                if (
                    !ultimaLeitura ||
                    (dataEdicaoRemota && dataEdicaoRemota > ultimaLeitura)
                ) {
                    local.visto_viagem = false;
                    local.viagem_atualizada = true;
                    alterou = true;

                    console.log("🔔 Nova edição REAL detectada:", local.id);
                }
            }

        });

        if (alterou) {
            saveSolicitacoes(lista);
        }

        atualizarNavbar();

    } catch (e) {
        console.error("Erro na sincronização", e);
        atualizarNavbar();
    }
}

function atualizarNavbar() {
    const lista = getSolicitacoes();

    const STATUS_SOLICITACAO = ["recusada", "cancelada"];

    const novasSolicitacoes = lista.filter(
        s => STATUS_SOLICITACAO.includes(s.status) && !s.visto_solicitacao
    ).length;

    // 🔔 QUALQUER viagem não vista gera badge
    const novasViagens = lista.filter(
        s => !s.visto_viagem
    ).length;

    if (document.body.dataset.page === "viagens-local") {
        atualizarBadge("badge-viagens", "nav-minhas-viagens", 0);
        return;
    }

    atualizarBadge(
        "badge-solicitacoes",
        "nav-minhas-solicitacoes",
        novasSolicitacoes
    );
    atualizarBadge(
        "badge-viagens",
        "nav-minhas-viagens",
        novasViagens
    );
}

function atualizarBadge(badgeId, linkId, qtd) {
    const badge = document.getElementById(badgeId);
    const link  = document.getElementById(linkId);

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
