console.log("encomendas.js carregado");

function renderEncomendasLocal() {
    const lista = getSolicitacoes()
        .filter(s => s.tipo === "encomenda")
        .sort((a, b) => new Date(b.data_solicitacao) - new Date(a.data_solicitacao));

    const container = document.getElementById("lista-encomendas");
    if (!container) return;

    if (!lista.length) {
        container.innerHTML = `
            <div class="alert alert-info text-center">
                Voce ainda nao fez nenhuma solicitacao de encomenda.
            </div>`;
        return;
    }

    container.innerHTML = "";

    lista.forEach(e => {
        const badgeClass =
            e.status === "pendente" ? "bg-warning text-dark" :
            e.status === "aceita"   ? "bg-success" :
                                      "bg-danger";

        container.innerHTML += `
            <div class="card border-0 shadow-sm rounded-3 mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between mb-2">
                        <h5>Encomenda para <strong>${e.carona_destino}</strong></h5>
                        <span class="badge ${badgeClass}">${e.status}</span>
                    </div>
                    <p class="mb-1"><strong>Descricao:</strong> ${e.descricao_item || "-"}</p>
                    <p class="mb-1"><strong>Motorista:</strong> ${e.motorista_nome}</p>
                    ${(e.status === "pendente" || e.status === "aceita") ? `
                    <button class="btn btn-sm btn-outline-danger mt-2"
                        onclick="cancelarEncomendaLocal(${e.id}, '${e.token_cancelamento}')">
                        Cancelar encomenda
                    </button>
                    ` : ""}
                </div>
            </div>`;
    });
}

async function cancelarEncomendaLocal(id, token) {
    if (!confirm("Tem certeza que deseja cancelar esta encomenda?")) return;

    try {
        const resp = await fetch(`/cancelar-solicitacao-publica/${id}/`, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCSRFToken(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({ token })
        });

        if (!resp.ok) {
            alert("Erro ao cancelar a encomenda.");
            return;
        }

        const lista = getSolicitacoes().map(s =>
            String(s.id) === String(id)
                ? { ...s, status: "cancelada", visto_solicitacao: true }
                : s
        );

        saveSolicitacoes(lista);
        renderEncomendasLocal();
        atualizarNavbar();
    } catch (e) {
        console.error("Erro ao cancelar encomenda", e);
    }
}

function marcarEncomendasComoVistas() {
    const lista = getSolicitacoes();
    let alterou = false;

    lista.forEach(s => {
        if (s.tipo === "encomenda" && s.status !== "pendente" && !s.visto_solicitacao) {
            s.visto_solicitacao = true;
            alterou = true;
        }
    });

    if (alterou) {
        saveSolicitacoes(lista);
        atualizarNavbar();
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    if (document.body.dataset.page !== "encomendas-local") return;

    await sincronizarSolicitacoes();
    await hidratarCaronas();
    marcarEncomendasComoVistas();
    renderEncomendasLocal();
});
