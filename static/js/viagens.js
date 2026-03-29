console.log("viagens.js carregado");

function renderViagensLocal() {
    const escAttr = (valor) =>
        String(valor ?? "")
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;");

    const formatarDataBr = (valor) => {
        if (!valor) return "";
        const txt = String(valor);
        const m = txt.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (m) return `${m[3]}/${m[2]}/${m[1]}`;
        const d = new Date(txt);
        return Number.isNaN(d.getTime()) ? txt : d.toLocaleDateString("pt-BR");
    };

    const dataHoraCarona = (s) => {
        const data = s.carona_data || "";
        const hora = (s.carona_hora || "00:00").slice(0, 5);
        return new Date(`${data}T${hora}:00`);
    };

    const lista = getSolicitacoes()
        .filter((s) =>
            String(s.status).toLowerCase() === "aceita" &&
            String(s.carona_status).toLowerCase() === "ativa"
        )
        .sort((a, b) => dataHoraCarona(a) - dataHoraCarona(b));

    const container = document.getElementById("lista-viagens");
    if (!container) return;
    container.innerHTML = "";

    if (!lista.length) {
        container.innerHTML = `
            <div class="alert alert-info text-center">Você ainda não tem viagens ativas.</div>
        `;
        return;
    }

    lista.forEach((v) => {
        container.innerHTML += `
            <div class="card card-viagem card-viagem-clickable mb-3"
                 data-bs-toggle="modal"
                 data-bs-target="#modalViagemLocal"
                 data-rota="${escAttr(`${v.carona_origem} -> ${v.carona_destino}`)}"
                 data-data-hora="${escAttr(`${formatarDataBr(v.carona_data)} as ${v.carona_hora}`)}"
                 data-motorista="${escAttr(v.motorista_nome)}"
                 data-quantidade="${escAttr(`${v.quantidade} vaga(s)`)}">
                <div class="card-body p-3">
                    <div class="viagem-header">
                        <div>
                            <div class="viagem-rota">
                                ${v.carona_origem} <i class="bi bi-arrow-right mx-1"></i> ${v.carona_destino}
                            </div>
                            <p class="viagem-meta">${v.carona_data} as ${v.carona_hora}</p>
                        </div>
                        <span class="badge bg-success">Ativa</span>
                    </div>
                    <div class="small mb-2"><strong>Motorista:</strong> ${v.motorista_nome}</div>
                    <div class="small mb-3"><strong>Quantidade:</strong> ${v.quantidade} vaga(s)</div>
                    <button class="btn btn-outline-danger btn-sm w-100"
                        onclick="cancelarViagemLocal(${v.id}, '${v.token_cancelamento}')">
                        <i class="bi bi-x-circle"></i> Cancelar viagem
                    </button>
                </div>
            </div>
        `;
    });
}

async function cancelarViagemLocal(id, token) {
    if (!confirm("Tem certeza que deseja cancelar sua participacao nesta viagem?")) {
        return;
    }

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
            alert("Erro ao cancelar a viagem.");
            return;
        }

        const lista = getSolicitacoes().map((s) =>
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

    lista.forEach((s) => {
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
        console.log("Viagens marcadas como vistas");
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    if (document.body.dataset.page !== "viagens-local") return;

    await sincronizarSolicitacoes();
    marcarViagensComoVistas();
    await hidratarCaronas();
    renderViagensLocal();

    const modalEl = document.getElementById("modalViagemLocal");
    if (modalEl) {
        modalEl.addEventListener("show.bs.modal", (event) => {
            const card = event.relatedTarget;
            if (!card) return;
            modalEl.querySelector('[data-local-viagem="rota"]').textContent = card.getAttribute("data-rota") || "-";
            modalEl.querySelector('[data-local-viagem="data_hora"]').textContent = card.getAttribute("data-data-hora") || "-";
            modalEl.querySelector('[data-local-viagem="motorista"]').textContent = card.getAttribute("data-motorista") || "-";
            modalEl.querySelector('[data-local-viagem="quantidade"]').textContent = card.getAttribute("data-quantidade") || "-";
        });
    }
});
