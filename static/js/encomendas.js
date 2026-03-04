console.log("encomendas.js carregado");

function badgeClass(status) {
    if (status === "pendente") return "bg-warning text-dark";
    if (status === "aceita") return "bg-success";
    return "bg-danger";
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
            body: new URLSearchParams({ token }),
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

function renderEncomendasLocal() {
    const container = document.getElementById("lista-encomendas");
    if (!container) return;

    const params = new URLSearchParams(window.location.search);
    const mostrarTodas = params.get("todas") === "1";
    const caronaFiltro = params.get("carona");
    const lista = getSolicitacoes()
        .filter(s => s.tipo === "encomenda")
        .sort((a, b) => new Date(b.data_solicitacao) - new Date(a.data_solicitacao));

    if (!lista.length) {
        container.innerHTML = `
            <div class="alert alert-info text-center">
                Voce ainda nao fez nenhuma solicitacao de encomenda.
            </div>`;
        return;
    }

    if (mostrarTodas) {
        container.innerHTML = lista.map(e => `
            <div class="card border-0 shadow-sm rounded-3 mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between flex-wrap mb-2">
                        <h5 class="card-title mb-0">Encomenda para <strong>${e.carona_destino || "-"}</strong></h5>
                        <span class="badge ${badgeClass(e.status)}">${e.status}</span>
                    </div>
                    <p class="mb-1 text-muted">Solicitado em: ${e.data_solicitacao || "-"}</p>
                    <p class="mb-1"><strong>Motorista:</strong> ${e.motorista_nome || "-"}</p>
                    <p class="mb-1"><strong>Rota:</strong> ${(e.carona_origem || "-")} -> ${(e.carona_destino || "-")}</p>
                    <p class="mb-2"><strong>Descricao:</strong> ${e.descricao_item || "-"}</p>
                    ${(e.status === "pendente" || e.status === "aceita") ? `
                        <button type="button" class="btn btn-danger btn-sm"
                            onclick="cancelarEncomendaLocal(${e.id}, '${e.token_cancelamento}')">
                            Cancelar Encomenda
                        </button>` : ""}
                </div>
            </div>
        `).join("");
        return;
    }

    const ativas = lista.filter(e =>
        (e.status === "pendente" || e.status === "aceita") &&
        (!e.carona_status || e.carona_status === "ativa")
    );

    const viagensMap = {};
    ativas.forEach(e => {
        const key = String(e.carona_id);
        if (!viagensMap[key]) {
            viagensMap[key] = {
                origem: e.carona_origem,
                destino: e.carona_destino,
                data: e.carona_data,
                hora: e.carona_hora,
                encomendas_ativas: 0,
                encomendas_pendentes: 0,
            };
        }
        viagensMap[key].encomendas_ativas += 1;
        if (e.status === "pendente") viagensMap[key].encomendas_pendentes += 1;
    });

    const viagensHtml = Object.entries(viagensMap).map(([caronaId, v]) => `
        <div class="col-lg-6">
            <a class="text-decoration-none text-reset d-block h-100" href="?carona=${caronaId}">
            <div class="border rounded-3 p-3 h-100 bg-white">
                <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
                    <div>
                        <div class="fw-semibold">${v.origem || "-"} -> ${v.destino || "-"}</div>
                        <div class="text-muted small">${v.data || "-"} ${v.hora ? "as " + v.hora : ""}</div>
                    </div>
                    <span class="badge bg-success">${v.encomendas_ativas} encomenda(s)</span>
                </div>
                <div class="d-flex gap-2 mb-1">
                    ${v.encomendas_pendentes > 0 ? `<span class="badge bg-warning text-dark">${v.encomendas_pendentes} pendente(s)</span>` : ""}
                </div>
                <span class="btn btn-sm btn-outline-primary mt-2">Ver ativas da viagem</span>
            </div>
            </a>
        </div>
    `).join("");

    const baseListaDetalhes = caronaFiltro
        ? ativas.filter(e => String(e.carona_id) === String(caronaFiltro))
        : lista.slice(0, 5);

    const detalhesTitulo = caronaFiltro ? "Ativas da viagem selecionada" : "Encomendas mais recentes";
    const detalhesHtml = baseListaDetalhes.map(e => `
        <div class="card border-0 shadow-sm rounded-3 mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
                    <div>
                        <h6 class="mb-0">Para ${e.carona_destino || "-"}</h6>
                        <div class="text-muted small">${e.carona_origem || "-"} -> ${e.carona_destino || "-"}</div>
                    </div>
                    <span class="badge ${badgeClass(e.status)}">${e.status}</span>
                </div>
                <p class="mb-1"><strong>Descricao:</strong> ${e.descricao_item || "-"}</p>
                <p class="text-muted small mb-0">Solicitado em ${e.data_solicitacao || "-"}</p>
                ${(e.status === "pendente" || e.status === "aceita") ? `
                    <button type="button" class="btn btn-outline-danger btn-sm mt-2"
                        onclick="cancelarEncomendaLocal(${e.id}, '${e.token_cancelamento}')">
                        Cancelar encomenda
                    </button>` : ""}
            </div>
        </div>
    `).join("");

    container.innerHTML = `
        <div class="card border-0 shadow-sm rounded-4 mb-4" style="background: linear-gradient(135deg, #f8fbff 0%, #eef6ff 100%);">
            <div class="card-body p-4">
                <h5 class="fw-bold mb-3">Ativas agora</h5>
                ${viagensHtml ? `<div class="row g-3">${viagensHtml}</div>` : `<div class="alert alert-info mb-0">Nenhuma viagem ativa com encomendas no momento.</div>`}
            </div>
        </div>

        <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="fw-bold mb-0">${detalhesTitulo}</h5>
            ${caronaFiltro ? `<a href="${window.location.pathname}" class="btn btn-sm btn-outline-secondary">Limpar filtro</a>` : ""}
        </div>
        ${detalhesHtml || `<div class="alert alert-info">Nenhuma encomenda ativa para esta viagem.</div>`}
    `;
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
