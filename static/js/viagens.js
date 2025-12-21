console.log("🚗 viagens.js carregado");

function renderViagensLocal() {
    const lista = getSolicitacoes()
        .filter(s =>
            String(s.status).toLowerCase() === "aceita" &&
            String(s.carona_status).toLowerCase() === "ativa"
        )
        .sort((a, b) =>
            new Date(b.data_solicitacao) - new Date(a.data_solicitacao)
        );

    const container = document.getElementById("lista-viagens");
    container.innerHTML = "";

    if (!lista.length) {
        container.innerHTML = `
            <div class="text-muted text-center py-4">
                Você não possui viagens ativas no momento.
            </div>
        `;
        return;
    }

    container.innerHTML = "";

    lista.forEach(v => {
        container.innerHTML += `
            <div class="card border-0 shadow-sm rounded-3 mb-3">
                <div class="card-body">
                    <h5>Viagem para <strong>${v.carona_destino}</strong></h5>
                    <p><strong>Saída:</strong> ${v.carona_data} às ${v.carona_hora}</p>
                    <p><strong>Local:</strong> ${v.carona_origem}</p>
                    <p><strong>Motorista:</strong> ${v.motorista_nome}</p>
                    <p><strong>Quantidade:</strong> ${v.quantidade}</p>
                    <button 
                        class="btn btn-outline-danger btn-sm w-100"
                        onclick="cancelarViagemLocal(${v.id}, '${v.token_cancelamento}')">
                        <i class="bi bi-x-circle"></i> Cancelar viagem
                    </button>
                </div>
            </div>`;
    });
}

async function cancelarViagemLocal(id, token) {
    if (!confirm("Tem certeza que deseja cancelar sua participação nesta viagem?")) {
        return;
    }

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
            alert("Erro ao cancelar a viagem.");
            return;
        }

        const lista = getSolicitacoes().map(s => {
            if (String(s.id) === String(id)) {
                return { ...s, status: "cancelada" };
            }
            return s;
        });

saveSolicitacoes(lista);

        // re-render
        renderViagensLocal();
        atualizarNavbar();

    } catch (e) {
        console.error("Erro ao cancelar viagem", e);
        alert("Erro inesperado ao cancelar a viagem.");
    }
}


document.addEventListener("DOMContentLoaded", async () => {
    console.log("📄 viagens.js carregado");

    if (document.body.dataset.page !== "viagens-local") return;

    await sincronizarSolicitacoes();
    await hidratarCaronas();
    renderViagensLocal();

const lista = getSolicitacoes().map(s => {
    if (s.status === "aceita") {
        return {
            ...s,
            visto_viagem: true
        };
    }
    return s;
});

saveSolicitacoes(lista);
atualizarNavbar();

});


