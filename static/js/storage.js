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
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
}

function saveSolicitacoes(lista) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lista));
}

function cancelarSolicitacaoLS(id) {
    const lista = getSolicitacoes().filter(s => String(s.id) !== String(id));
    saveSolicitacoes(lista);
}




