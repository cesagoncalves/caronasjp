document.addEventListener("DOMContentLoaded", () => {
    const modalEl = document.getElementById("modalEditarVagas");
    const form = document.getElementById("formEditarVagas");
    const input = document.getElementById("quantidadeEditarVagas");
    const erro = document.getElementById("erroEditarVagas");
    if (!modalEl || !form) return;
    let atual = null;
    let modalPai = null;

    const atualizarAcoesLocais = () => {
        if (typeof getSolicitacoes !== "function") return;
        document.querySelectorAll(".js-acoes-participacao").forEach(bloco => {
            if (bloco.querySelector(".js-editar-vagas")) return;
            const reserva = getSolicitacoes().find(s => String(s.carona_id) === bloco.dataset.caronaId && s.tipo !== "encomenda" && ["aceita", "pendente"].includes(s.status));
            if (!reserva || !reserva.token_cancelamento) return;
            bloco.querySelector(".js-solicitar-vaga")?.remove();
            const editar = document.createElement("button");
            editar.type = "button";
            editar.className = "btn btn-primary js-editar-vagas";
            editar.textContent = "Editar vagas";
            editar.dataset.id = reserva.id;
            editar.dataset.quantidade = reserva.quantidade;
            editar.dataset.status = reserva.status;
            editar.dataset.token = reserva.token_cancelamento;
            const cancelar = document.createElement("button");
            cancelar.type = "button";
            cancelar.className = "btn btn-outline-danger";
            cancelar.textContent = "Cancelar participação";
            cancelar.addEventListener("click", async () => {
                if (!confirm("Cancelar sua participação nesta viagem?")) return;
                cancelar.disabled = true;
                try {
                    const resposta = await fetch(`/cancelar-solicitacao-publica/${reserva.id}/`, {
                        method: "POST", headers: {"X-CSRFToken": getCSRFToken()},
                        body: new URLSearchParams({token: reserva.token_cancelamento}),
                    });
                    if (!resposta.ok) throw new Error("Não foi possível cancelar. Atualize a página e tente novamente.");
                    saveSolicitacoes(getSolicitacoes().filter(s => String(s.id) !== String(reserva.id)));
                    window.location.reload();
                } catch (e) { alert(e.message); cancelar.disabled = false; }
            });
            bloco.prepend(editar, cancelar);
        });
    };
    document.addEventListener("show.bs.modal", atualizarAcoesLocais);
    atualizarAcoesLocais();

    document.addEventListener("click", event => {
        const botao = event.target.closest(".js-editar-vagas");
        if (!botao) return;
        event.preventDefault();
        event.stopPropagation();
        atual = {...botao.dataset};
        const bloco = botao.closest(".js-acoes-participacao");
        input.value = atual.quantidade;
        input.removeAttribute("max");
        if (bloco) input.max = Number(bloco.dataset.vagas) + (atual.status === "aceita" ? Number(atual.quantidade) : 0);
        erro.classList.add("d-none");
        modalPai = botao.closest(".modal");
        const abrir = () => bootstrap.Modal.getOrCreateInstance(modalEl).show();
        if (modalPai) {
            modalPai.addEventListener("hidden.bs.modal", abrir, {once:true});
            bootstrap.Modal.getOrCreateInstance(modalPai).hide();
        } else abrir();
    });
    input.addEventListener("input", () => {
        if (input.max && Number(input.value) > Number(input.max)) input.value = input.max;
    });
    modalEl.addEventListener("hidden.bs.modal", () => {
        if (modalPai) bootstrap.Modal.getOrCreateInstance(modalPai).show();
        modalPai = null;
    });
    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (!atual || !form.reportValidity()) return;
        const enviar = form.querySelector('[type="submit"]');
        enviar.disabled = true;
        try {
            const resposta = await fetch(`/solicitacao/${atual.id}/editar-vagas/`, {
                method:"POST", headers:{"X-CSRFToken":getCSRFToken()},
                body:new URLSearchParams({quantidade:input.value, token:atual.token || ""}),
            });
            const dados = await resposta.json();
            if (!resposta.ok) {
                if (dados.max !== undefined) input.max = dados.max;
                throw new Error(dados.erro || "Não foi possível editar as vagas.");
            }
            if (typeof getSolicitacoes === "function") {
                saveSolicitacoes(getSolicitacoes().map(s => String(s.id) === atual.id ? {...s, quantidade:dados.quantidade, status:dados.status} : s));
            }
            window.location.reload();
        } catch (e) {
            erro.textContent = e.message;
            erro.classList.remove("d-none");
        } finally { enviar.disabled = false; }
    });
});
