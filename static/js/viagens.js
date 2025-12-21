console.log("🚗 viagens.js carregado");

function renderViagensLocal() {
    const lista = getSolicitacoes()
    .filter(s => String(s.status).toLowerCase() === "aceita")
    .sort(
        (a, b) => new Date(b.data_solicitacao) - new Date(a.data_solicitacao)
    );


    const container = document.getElementById("lista-viagens");

    if (!container) return;

    if (lista.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info text-center">
                Você ainda não tem viagens aceitas.
            </div>`;
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
                </div>
            </div>`;
    });
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


