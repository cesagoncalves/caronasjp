document.addEventListener("DOMContentLoaded", () => {
    const modalidade = document.getElementById("id_modalidade");
    if (!modalidade) return;
    const vagas = document.getElementById("id_vagas");
    const tipo = document.getElementById("id_tipo_valor");
    const atualizar = () => {
        const somenteEncomendas = modalidade.value === "encomenda";
        for (const field of [vagas, tipo]) {
            field.closest(".mb-3").classList.toggle("d-none", somenteEncomendas);
            field.disabled = somenteEncomendas;
        }
        const valor = document.getElementById("id_valor");
        const mostrarValor = !somenteEncomendas && tipo.value === "dinheiro";
        document.getElementById("campo-valor").classList.toggle("d-none", !mostrarValor);
        valor.disabled = !mostrarValor;
        vagas.min = somenteEncomendas ? 0 : 1;
    };
    modalidade.addEventListener("change", atualizar);
    tipo.addEventListener("change", atualizar);
    atualizar();
});
