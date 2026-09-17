console.log("🧠 storage.js carregado");

const STORAGE_KEY = "solicitacoes_passageiro";

async function hidratarCaronas() {
    const solicitacoes = getSolicitacoes();
    if (!solicitacoes.length) return;

    const caronaIds = [...new Set(solicitacoes.map(s => s.carona_id))];

    const res = await fetch(
        `/api/estado-caronas/?ids=${caronaIds.join(",")}`
    );
    const data = await res.json();

    const mapa = {};
    data.result.forEach(c => {
        mapa[c.id] = c;
    });

    const atualizadas = solicitacoes.map(s => {
        const carona = mapa[s.carona_id];
        if (!carona) return s;

        return {
            ...s,
            carona_origem: carona.origem,
            carona_destino: carona.destino,
            carona_data: carona.data,
            carona_hora: carona.hora,
            motorista_nome: carona.motorista_nome,
            carona_status: carona.status
        };
    });

    saveSolicitacoes(atualizadas);
}


function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
}

function getSolicitacoes() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch (e) {
        console.warn("Falha ao ler solicitacoes do localStorage, limpando cache.", e);
        localStorage.removeItem(STORAGE_KEY);
        return [];
    }
}

function saveSolicitacoes(lista) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lista));
}

function cancelarSolicitacaoLS(id) {
    const lista = getSolicitacoes().filter(s => String(s.id) !== String(id));
    saveSolicitacoes(lista);
}





function formatarDataLocal(valor, incluirHora = false) {
    if (!valor) return "-";
    const texto = String(valor);
    const data = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto);
    if (data) return `${data[3]}/${data[2]}/${data[1]}`;
    const instante = new Date(texto);
    if (Number.isNaN(instante.getTime())) return texto;
    return incluirHora ? instante.toLocaleString("pt-BR", {dateStyle:"short", timeStyle:"short"}) : instante.toLocaleDateString("pt-BR");
}
