console.log("🔔 notificacoes.js carregado");

async function sincronizarSolicitacoes() {
    const lista = getSolicitacoes();
    if (!lista.length) return;

    const ids = lista.map(s => s.id).join(",");

    try {
        const resp = await fetch(`/api/status-solicitacoes/?ids=${ids}`);
        if (!resp.ok) return;

        const data = await resp.json();
        const backend = data.result || [];

        let alterou = false;

        lista.forEach(local => {
            const remoto = backend.find(b => String(b.id) === String(local.id));
            if (!remoto) return;

            if (local.status !== remoto.status) {
                local.status = remoto.status;

                // 🔔 notificação de solicitação
                local.visto_solicitacao = false;

                // 🚗 notificação de viagem
                if (remoto.status === "aceita") {
                    local.visto_viagem = false;
                }

                alterou = true;
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

    const novasSolicitacoes = lista.filter(
        s => s.status !== "pendente" && !s.visto_solicitacao
    ).length;

    const novasViagens = lista.filter(
        s => s.status === "aceita" && !s.visto_viagem
    ).length;

    atualizarBadge("badge-solicitacoes", "nav-minhas-solicitacoes", novasSolicitacoes);
    atualizarBadge("badge-viagens", "nav-minhas-viagens", novasViagens);
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
