console.log("historico.js carregado");

let filtroHistoricoLocal = "todas";

function atualizarBotoesFiltroHistorico() {
    document.querySelectorAll("#filtros-historico-local [data-tipo]").forEach((btn) => {
        const ativo = btn.dataset.tipo === filtroHistoricoLocal;
        btn.classList.toggle("is-active", ativo);
    });
}

function renderHistoricoLocal() {
    const listaBase = getSolicitacoes()
        .filter(s => s.status === "aceita" && s.carona_status === "concluida")
        .sort((a, b) => new Date(b.data_solicitacao) - new Date(a.data_solicitacao));

    const lista = listaBase.filter((s) => {
        if (filtroHistoricoLocal === "todas") return true;
        const tipo = (s.tipo || "carona").toLowerCase();
        return tipo === filtroHistoricoLocal;
    });

    const container = document.getElementById("lista-historico");
    if (!container) return;

    if (lista.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info text-center">
                Nenhum item encontrado no historico.
            </div>`;
        return;
    }

    container.innerHTML = "";

    lista.forEach(s => {
        const tipo = (s.tipo || "carona").toLowerCase();
        const badge = tipo === "encomenda"
            ? `<span class="badge bg-warning text-dark"><i class="bi bi-box-seam me-1"></i> Voce enviou encomenda</span>`
            : `<span class="badge bg-success"><i class="bi bi-person-fill"></i> Voce foi passageiro</span>`;

        container.innerHTML += `
            <div class="card border-0 shadow-sm rounded-3 mb-3">
                <div class="card-body">
                    <h5 class="mb-1">${s.carona_origem} -> <strong>${s.carona_destino}</strong></h5>
                    <p class="mb-1"><strong>Data:</strong> ${s.carona_data} as ${s.carona_hora}</p>
                    <p class="mb-1"><strong>Motorista:</strong> ${s.motorista_nome}</p>
                    ${tipo === "encomenda" ? `<p class="mb-1"><strong>Item:</strong> ${s.descricao_item || "-"}</p>` : ""}
                    ${badge}
                </div>
            </div>
        `;
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    if (document.body.dataset.page !== "historico-local") return;

    const filtros = document.getElementById("filtros-historico-local");
    if (filtros) {
        filtros.addEventListener("click", (event) => {
            const btn = event.target.closest("[data-tipo]");
            if (!btn) return;
            filtroHistoricoLocal = btn.dataset.tipo || "todas";
            atualizarBotoesFiltroHistorico();
            renderHistoricoLocal();
        });
        atualizarBotoesFiltroHistorico();
    }

    await sincronizarSolicitacoes();
    await hidratarCaronas();
    renderHistoricoLocal();
    atualizarNavbar();
});
