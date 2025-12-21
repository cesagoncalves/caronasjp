console.log("📜 historico.js carregado");

function renderHistoricoLocal() {
    const lista = getSolicitacoes()
        .filter(s =>
            s.status === "aceita" &&
            s.carona_status === "concluida"
        )
        .sort(
            (a, b) => new Date(b.data_solicitacao) - new Date(a.data_solicitacao)
        );

    const container = document.getElementById("lista-historico");


    if (!container) return;

    if (lista.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info text-center">
                Você ainda não possui histórico de viagens.
            </div>`;
        return;
    }

    container.innerHTML = "";

    lista.forEach(s => {

        container.innerHTML += `
            <div class="card border-0 shadow-sm rounded-3 mb-3">
                <div class="card-body">

                    <div class="d-flex justify-content-between align-items-start">
                        <h5 class="mb-1">
                            ${s.carona_origem} → <strong>${s.carona_destino}</strong>
                        </h5>

                    </div>

                    <p class="mb-1">
                        <strong>Data:</strong> ${s.carona_data} às ${s.carona_hora}
                    </p>

                    <p class="mb-1">
                        <strong>Motorista:</strong> ${s.motorista_nome}
                    </p>

                    <p class="mb-1">
                        <strong>Quantidade:</strong> ${s.quantidade}
                    </p>

                    <span class="badge bg-secondary">
                        Passageiro
                    </span>

                </div>
            </div>
        `;
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    if (document.body.dataset.page !== "historico-local") return;

    await sincronizarSolicitacoes();
    await hidratarCaronas();
    renderHistoricoLocal();
    atualizarNavbar();
});
