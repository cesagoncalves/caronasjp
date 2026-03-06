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

    const dataHoraCarona = (s) => {
        const data = s.carona_data || "";
        const hora = (s.carona_hora || "00:00").slice(0, 5);
        return new Date(`${data}T${hora}:00`);
    };

    const params = new URLSearchParams(window.location.search);
    const mostrarTodas = params.get("todas") === "1";
    const paginaAtual = Math.max(parseInt(params.get("page") || "1", 10), 1);
    const itensPorPagina = 12;
    const limiteRecentes = 6;
    const lista = getSolicitacoes()
        .filter(s => s.tipo === "encomenda")
        .sort((a, b) => dataHoraCarona(a) - dataHoraCarona(b));

    if (!lista.length) {
        container.innerHTML = `
            <div class="alert alert-info text-center">
                Voce ainda nao fez nenhuma solicitacao de encomenda.
            </div>`;
        return;
    }

    if (mostrarTodas) {
        const totalPaginas = Math.max(1, Math.ceil(lista.length / itensPorPagina));
        const pagina = Math.min(paginaAtual, totalPaginas);
        const inicio = (pagina - 1) * itensPorPagina;
        const itensPagina = lista.slice(inicio, inicio + itensPorPagina);
        const paginacao = totalPaginas > 1 ? `
            <nav aria-label="Paginacao de encomendas" class="mt-3">
                <ul class="pagination justify-content-center mb-0">
                    ${pagina > 1 ? `<li class="page-item"><a class="page-link" href="?todas=1&page=${pagina - 1}">Anterior</a></li>` : ""}
                    <li class="page-item disabled"><span class="page-link">Pagina ${pagina} de ${totalPaginas}</span></li>
                    ${pagina < totalPaginas ? `<li class="page-item"><a class="page-link" href="?todas=1&page=${pagina + 1}">Proxima</a></li>` : ""}
                </ul>
            </nav>
        ` : "";
        container.innerHTML = itensPagina.map(e => `
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
        `).join("") + paginacao;
        return;
    }

    const ativas = lista.filter(e =>
        e.status === "aceita" &&
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
    });

    const viagensHtml = Object.entries(viagensMap).map(([caronaId, v]) => `
        <div class="col-lg-6">
            <a class="text-decoration-none text-reset d-block h-100" href="/minhas-encomendas/publica/carona/${caronaId}/">
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
                <span class="btn btn-sm btn-outline-primary mt-2">Ver minhas encomendas da viagem</span>
            </div>
            </a>
        </div>
    `).join("");

    const baseListaDetalhes = lista.slice(0, limiteRecentes);
    const detalhesTitulo = "Encomendas mais recentes";
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

    const verTodasLink = lista.length > limiteRecentes ? `
        <div class="mb-3 text-center position-relative">
            <h5 class="fw-bold mb-1">Encomendas mais recentes</h5>
            <a href="?todas=1" class="d-none d-md-inline small text-primary text-decoration-none fw-semibold position-absolute end-0 top-50 translate-middle-y">
                Ver todas →
            </a>
            <a href="?todas=1" class="d-inline d-md-none small text-primary text-decoration-none fw-semibold">
                Ver todas →
            </a>
        </div>
    ` : `
        <div class="mb-3 text-center">
            <h5 class="fw-bold mb-0">Encomendas mais recentes</h5>
        </div>
    `;

    container.innerHTML = `
        <div class="card border-0 shadow-sm rounded-4 mb-4" style="background: linear-gradient(135deg, #f8fbff 0%, #eef6ff 100%);">
            <div class="card-body p-4">
                <h5 class="fw-bold mb-3">Viagens ativas com suas encomendas</h5>
                ${viagensHtml ? `<div class="row g-3">${viagensHtml}</div>` : `<div class="alert alert-info mb-0">Nenhuma viagem ativa com encomendas no momento.</div>`}
            </div>
        </div>

        ${verTodasLink}
        ${detalhesHtml || `<div class="alert alert-info">Nenhuma encomenda ativa para esta viagem.</div>`}
    `;
}

function renderEncomendasCaronaLocal() {
    const container = document.getElementById("encomenda-carona-local");
    const caronaId = document.body.dataset.caronaId;
    if (!container || !caronaId) return;

    const lista = getSolicitacoes()
        .filter(s =>
            s.tipo === "encomenda" &&
            String(s.carona_id) === String(caronaId) &&
            s.status === "aceita"
        )
        .sort((a, b) => {
            const da = new Date(a.data_solicitacao || 0);
            const db = new Date(b.data_solicitacao || 0);
            return db - da;
        });

    if (!lista.length) {
        container.innerHTML = `<div class="alert alert-info">Nenhuma encomenda encontrada para esta viagem.</div>`;
        return;
    }

    const tituloOrigem = lista[0].carona_origem || "-";
    const tituloDestino = lista[0].carona_destino || "-";
    const tituloData = lista[0].carona_data || "-";
    const tituloHora = (lista[0].carona_hora || "").slice(0, 5);

    container.innerHTML = `
        <div class="alert alert-light border">
            <strong>${tituloOrigem} -> ${tituloDestino}</strong>
            em ${tituloData} ${tituloHora ? "as " + tituloHora : ""}
        </div>
        ${lista.map(e => `
            <div class="card border-0 shadow-sm rounded-3 mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
                        <div>
                            <div class="fw-semibold">${e.carona_origem || "-"} -> ${e.carona_destino || "-"}</div>
                            <div class="text-muted small">Solicitada em ${e.data_solicitacao || "-"}</div>
                        </div>
                    </div>
                    <p class="mb-2"><strong>Descricao:</strong> ${e.descricao_item || "-"}</p>
                    ${e.endereco_solicitante ? `<p class="mb-1 small text-muted"><i class="bi bi-geo-alt-fill me-1"></i>Coleta: ${e.endereco_solicitante}</p>` : ""}
                    ${e.endereco_destino_solicitante ? `<p class="mb-2 small text-muted"><i class="bi bi-signpost-2-fill me-1"></i>Entrega: ${e.endereco_destino_solicitante}</p>` : ""}
                    ${(e.status === "pendente" || e.status === "aceita") ? `
                        <button type="button" class="btn btn-outline-danger btn-sm"
                            onclick="cancelarEncomendaLocal(${e.id}, '${e.token_cancelamento}')">
                            <i class="bi bi-x-circle"></i> Cancelar encomenda
                        </button>` : ""}
                </div>
            </div>
        `).join("")}
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
    const page = document.body.dataset.page;
    if (page !== "encomendas-local" && page !== "encomendas-carona-local") return;
    await sincronizarSolicitacoes();
    await hidratarCaronas();
    marcarEncomendasComoVistas();
    if (page === "encomendas-carona-local") {
        renderEncomendasCaronaLocal();
        return;
    }
    renderEncomendasLocal();
});
