/* ============================================================
   ARMAZENAMENTO LOCAL DO PASSAGEIRO (SEM LOGIN)
   ============================================================ */

console.log("🔥 JS GLOBAL DE NOTIFICAÇÕES CARREGADO");
const STORAGE_KEY = "solicitacoes_passageiro";

/* ============================================================
   LOCALSTORAGE
   ============================================================ */

function carregarSolicitacoesLS() {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
}

function salvarSolicitacoesLS(lista) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lista));
}

function cancelarSolicitacaoLS(id) {
    const lista = carregarSolicitacoesLS().filter(s => String(s.id) !== String(id));
    salvarSolicitacoesLS(lista);
}

/* ============================================================
   SINCRONIZAÇÃO COM BACKEND (STATUS PELO UUID)
   ============================================================ */

async function sincronizarStatusComBackend() {
    const lista = carregarSolicitacoesLS();

    if (lista.length === 0) {
        console.log("ℹ️ Nenhuma solicitação no localStorage");
        return;
    }

    try {
        // Monta query string usando os UUIDs
        const ids = lista.map(s => s.id).join(",");
        const response = await fetch(`/api/status-solicitacoes/?ids=${ids}`);

        if (!response.ok) {
            console.error("❌ Erro HTTP ao consultar status das solicitações");
            return;
        }

        const data = await response.json();
        const backendSolicitacoes = Array.isArray(data.result) ? data.result : [];

        if (backendSolicitacoes.length === 0) {
            console.warn("⚠️ Nenhuma solicitação válida vinda do backend");
            return;
        }

        let alterou = false;

        lista.forEach(local => {
            const backend = backendSolicitacoes.find(b => String(b.id) === String(local.id));
            if (!backend) return;

            const statusLocal = String(local.status).trim().toLowerCase();
            const statusBackend = String(backend.status).trim().toLowerCase();

            if (statusLocal !== statusBackend) {
                console.log(`✅ Atualizando status (${local.id}): ${statusLocal} → ${statusBackend}`);
                local.status = statusBackend;
                local.visto = false;
                alterou = true;
            }
        });

        if (alterou) {
            salvarSolicitacoesLS(lista);
            renderSolicitacoesLocal();
            renderViagensLocal();
            console.log("💾 LocalStorage atualizado e UI sincronizada");
        } else {
            console.log("ℹ️ Nenhuma mudança de status detectada");
        }

    } catch (err) {
        console.error("❌ Erro na sincronização:", err);
    }
}

/* ============================================================
   RENDER - MINHAS SOLICITAÇÕES
   ============================================================ */

function renderSolicitacoesLocal() {
    const lista = carregarSolicitacoesLS();
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
                        <button class="btn btn-danger btn-sm" onclick="cancelarLocal('${s.id}')">
                            Cancelar
                        </button>` : ""}
                </div>
            </div>`;
    });
}

/* ============================================================
   RENDER - MINHAS VIAGENS (ACEITAS)
   ============================================================ */

function renderViagensLocal() {
    const lista = carregarSolicitacoesLS().filter(
        s => String(s.status).toLowerCase() === "aceita"
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

/* ============================================================
   NOTIFICAÇÕES NA NAVBAR (GLOBAL)
   ============================================================ */

function atualizarNavbarPassageiro() {
    const lista = carregarSolicitacoesLS();

    const pendentesNaoVistas = lista.filter(
        s => s.status !== "pendente" && !s.visto
    );

    const badge = document.getElementById("badge-solicitacoes");
    const link  = document.getElementById("nav-minhas-solicitacoes");

    if (!badge || !link) return;

    if (pendentesNaoVistas.length > 0) {
        badge.textContent = pendentesNaoVistas.length;
        badge.classList.remove("d-none");
        link.classList.add("text-warning", "fw-bold");
    } else {
        badge.classList.add("d-none");
        link.classList.remove("text-warning", "fw-bold");
    }
}

/* ============================================================
   EXECUÇÃO AUTOMÁTICA
   ============================================================ */

(async function () {

    // 🔁 SEMPRE sincroniza (navbar depende disso)
    await sincronizarStatusComBackend();

    // 🔔 Atualiza navbar em qualquer página
    atualizarNavbarPassageiro();

    const page = document.body.dataset.page;

    if (page === "solicitacoes-local") {
        renderSolicitacoesLocal();

        // marcou como visto ao entrar
        const lista = carregarSolicitacoesLS().map(s => {
            s.visto = true;
            return s;
        });
        salvarSolicitacoesLS(lista);
        atualizarNavbarPassageiro();
    }

    if (page === "viagens-local") {
        renderViagensLocal();

        const lista = carregarSolicitacoesLS().map(s => {
            s.visto = true;
            return s;
        });
        salvarSolicitacoesLS(lista);
        atualizarNavbarPassageiro();
    }

})();

/* ============================================================
   EXPOSIÇÃO PARA DEBUG
   ============================================================ */

window.sincronizarStatusComBackend = sincronizarStatusComBackend;
window.renderSolicitacoesLocal = renderSolicitacoesLocal;
window.renderViagensLocal = renderViagensLocal;
