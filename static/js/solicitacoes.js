console.log("solicitacoes.js carregado");

function labelStatus(status) {
    const valor = String(status || "").toLowerCase();
    if (valor === "pendente") return "Pendente";
    if (valor === "aceita") return "Aceita";
    if (valor === "recusada") return "Recusada";
    if (valor === "cancelada") return "Cancelada";
    return status || "Status";
}

function classeStatus(status) {
    const valor = String(status || "").toLowerCase();
    if (valor === "pendente") return "bg-warning text-dark";
    if (valor === "aceita") return "bg-success";
    return "bg-danger";
}

function formatarDataBr(valor) {
    if (!valor) return "";
    const txt = String(valor);
    const m = txt.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (m) return `${m[3]}/${m[2]}/${m[1]}`;
    const d = new Date(txt);
    return Number.isNaN(d.getTime()) ? txt : d.toLocaleDateString("pt-BR");
}

function renderSolicitacoesLocal() {
    const lista = getSolicitacoes()
        .filter((s) => s.tipo !== "encomenda")
        .sort((a, b) => new Date(b.data_solicitacao) - new Date(a.data_solicitacao));

    const container = document.getElementById("lista-solicitacoes");
    if (!container) return;

    if (!lista.length) {
        container.innerHTML = `
            <div class="alert alert-info text-center">Voce ainda nao tem solicitacoes.</div>`;
        return;
    }

    container.innerHTML = "";

    lista.forEach((s) => {
        const badgeClass = classeStatus(s.status);
        const statusLabel = labelStatus(s.status);
        const dataHora = `${formatarDataBr(s.carona_data)}${s.carona_hora ? ` as ${s.carona_hora}` : ""}`;

        container.innerHTML += `
            <div class="card card-solicitacao mb-3">
                <div class="card-body p-3">
                    <div class="solicitacao-head">
                        <div>
                            <div class="solicitacao-rota">
                                ${s.carona_origem || "-"} <i class="bi bi-arrow-right mx-1"></i> ${s.carona_destino || "-"}
                            </div>
                            <p class="solicitacao-meta">${dataHora}</p>
                        </div>
                        <span class="badge ${badgeClass}">${statusLabel}</span>
                    </div>

                    <div class="small mb-1"><strong>Motorista:</strong> ${s.motorista_nome || "-"}</div>
                    <div class="small mb-2"><strong>Quantidade:</strong> ${s.quantidade || 0}</div>

                    <div class="d-flex justify-content-end pt-1">
                        ${String(s.status).toLowerCase() === "pendente" ? `
                            <button class="btn btn-danger btn-sm"
                                onclick="cancelarSolicitacaoPublica(${s.id}, '${s.token_cancelamento}')">
                                Cancelar solicitacao
                            </button>
                        ` : ""}
                    </div>
                </div>
            </div>`;
    });
}

async function cancelarSolicitacaoPublica(id, token) {
    if (!confirm("Tem certeza que deseja cancelar esta solicitacao?")) return;

    try {
        const resp = await fetch(`/cancelar-solicitacao-publica/${id}/`, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCSRFToken(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({
                token: token,
            }),
        });

        if (!resp.ok) {
            alert("Erro ao cancelar a solicitacao.");
            return;
        }

        const lista = getSolicitacoes().filter((s) => String(s.id) !== String(id));
        saveSolicitacoes(lista);

        renderSolicitacoesLocal();
        atualizarNavbar();
    } catch (e) {
        console.error("Erro ao cancelar solicitacao", e);
    }
}

function marcarSolicitacoesComoVistas() {
    const lista = getSolicitacoes();
    let alterou = false;

    lista.forEach((s) => {
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

    const lista = getSolicitacoes().map((s) => {
        if (s.tipo !== "encomenda" && s.status !== "pendente") {
            return { ...s, visto_solicitacao: true };
        }
        return s;
    });

    saveSolicitacoes(lista);
    atualizarNavbar();
});
