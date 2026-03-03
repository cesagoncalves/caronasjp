console.log("📄 solicitacoes.js carregado");

function renderSolicitacoesLocal() {
    const lista = getSolicitacoes()
        .filter(s => s.tipo !== "encomenda")
        .sort((a, b) => new Date(b.data_solicitacao) - new Date(a.data_solicitacao));
    const container = document.getElementById("lista-solicitacoes");

    if (!container) return;

    if (lista.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info text-center">
                Você ainda não fez nenhuma solicitação.
            </div>`;
        return;
    }

    container.innerHTML = "";

    lista.forEach(s => {
        const badgeClass =
            s.status === "pendente" ? "bg-warning text-dark" :
            s.status === "aceita"   ? "bg-success" :
                                      "bg-danger";

        container.innerHTML += `
            <div class="card border-0 shadow-sm rounded-3 mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between mb-2">
                        <h5>Carona para <strong>${s.carona_destino}</strong></h5>
                        <span class="badge ${badgeClass}">${s.status}</span>
                    </div>
                    <p class="mb-1"><strong>Quantidade:</strong> ${s.quantidade}</p>
                    <p class="mb-1"><strong>Motorista:</strong> ${s.motorista_nome}</p>
                    ${s.status === "pendente" ? `
                    <button class="btn btn-sm btn-outline-danger mt-2"
                        onclick="cancelarSolicitacaoPublica(${s.id}, '${s.token_cancelamento}')">
                        Cancelar solicitação
                    </button>
                ` : ""}
                </div>
            </div>`;
    });
}

async function cancelarSolicitacaoPublica(id, token) {
    if (!confirm("Tem certeza que deseja cancelar esta solicitação?")) return;

    try {
        const resp = await fetch(`/cancelar-solicitacao-publica/${id}/`, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCSRFToken(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({
                token: token
            })
        });

        if (!resp.ok) {
            alert("Erro ao cancelar a solicitação.");
            return;
        }

        // remove do localStorage
        const lista = getSolicitacoes().filter(s => String(s.id) !== String(id));
        saveSolicitacoes(lista);

        // re-renderiza
        renderSolicitacoesLocal();
        atualizarNavbar();

    } catch (e) {
        console.error("Erro ao cancelar solicitação", e);
    }
}

function marcarSolicitacoesComoVistas() {
    const lista = getSolicitacoes();
    let alterou = false;

    lista.forEach(s => {
        if (s.tipo !== "encomenda" && s.status !== "pendente" && !s.visto_solicitacao) {
            s.visto_solicitacao = true;
            alterou = true;
        }
    });

    if (alterou) {
        saveSolicitacoes(lista);
        atualizarNavbar();
    }
}

document.addEventListener("DOMContentLoaded", marcarSolicitacoesComoVistas);



document.addEventListener("DOMContentLoaded", async () => {
    if (document.body.dataset.page !== "solicitacoes-local") return;

    await sincronizarSolicitacoes();
    await hidratarCaronas();
    renderSolicitacoesLocal();

const lista = getSolicitacoes().map(s => {
    if (s.tipo !== "encomenda" && s.status !== "pendente") {
        return { ...s, visto_solicitacao: true };
    }
    return s;
});

saveSolicitacoes(lista);
atualizarNavbar();

});



