console.log("🧠 storage.js carregado");

const STORAGE_KEY = "solicitacoes_passageiro";


function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
}

function getSolicitacoes() {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
}

function saveSolicitacoes(lista) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lista));
}

function cancelarSolicitacaoLS(id) {
    const lista = getSolicitacoes().filter(s => String(s.id) !== String(id));
    saveSolicitacoes(lista);
}



