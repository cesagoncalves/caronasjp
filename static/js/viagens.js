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
            body: new URLSearchParams({ token })
        });

        if (!resp.ok) {
            alert("Erro ao cancelar a viagem.");
            return;
        }

        const lista = getSolicitacoes().map(s =>
            String(s.id) === String(id)
                ? { ...s, status: "cancelada", visto_viagem: true }
                : s
        );

        saveSolicitacoes(lista);
        renderViagensLocal();
        atualizarNavbar();

    } catch (e) {
        console.error("Erro ao cancelar viagem", e);
        alert("Erro inesperado ao cancelar a viagem.");
    }
}

function marcarViagensComoVistas() {
    const lista = getSolicitacoes();
    let alterou = false;

    lista.forEach(s => {
        if (!s.visto_viagem) {
            s.visto_viagem = true;
            s.viagem_atualizada = false;
            s.ultima_edicao_lida = new Date().toISOString();
            alterou = true;
        }
    });

    if (alterou) {
        saveSolicitacoes(lista);
        atualizarNavbar();
        console.log("👀 Viagens marcadas como vistas");
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    if (document.body.dataset.page !== "viagens-local") return;

    console.log("📄 Página Minhas Viagens");

    await sincronizarSolicitacoes(); // 🔄 pega edição/status do backend
    marcarViagensComoVistas();       // 👀 lê tudo
    await hidratarCaronas();
    renderViagensLocal();
});
