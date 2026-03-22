function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
}

function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return null;
    try {
        return await navigator.serviceWorker.register("/sw.js");
    } catch (err) {
        return null;
    }
}

async function subscribeToPush(registration, publicKey) {
    if (!registration || !publicKey) return null;
    const existing = await registration.pushManager.getSubscription();
    if (existing) return existing;
    return registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
}

async function sendSubscription(subscription, url) {
    const csrf = getCookie("csrftoken");
    const res = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf,
        },
        body: JSON.stringify(subscription),
    });
    return res.ok;
}

function setupPushPrompt() {
    const modalEl = document.getElementById("pushPromptModal");
    if (!modalEl) return;

    const publicKey = modalEl.getAttribute("data-public-key") || "";
    const subscribeUrl = modalEl.getAttribute("data-subscribe-url") || "";
    const skipUrl = modalEl.getAttribute("data-skip-url") || "";
    const show = modalEl.getAttribute("data-show") === "1";

    if (!publicKey || !subscribeUrl || !show) return;

    if (Notification.permission === "denied") {
        if (skipUrl) {
            fetch(skipUrl, {
                method: "POST",
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            });
        }
        return;
    }

    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    const btnEnable = modalEl.querySelector("[data-action='enable']");
    const btnLater = modalEl.querySelector("[data-action='later']");
    const statusEl = modalEl.querySelector("[data-role='status']");

    btnEnable.addEventListener("click", async () => {
        statusEl.textContent = "Preparando notificacoes...";
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
            statusEl.textContent = "Permissao negada. Voce pode ativar depois no navegador.";
            return;
        }

        const registration = await registerServiceWorker();
        if (!registration) {
            statusEl.textContent = "Nao foi possivel registrar o service worker.";
            return;
        }

        const sub = await subscribeToPush(registration, publicKey);
        if (!sub) {
            statusEl.textContent = "Falha ao criar assinatura.";
            return;
        }

        const ok = await sendSubscription(sub, subscribeUrl);
        if (ok) {
            statusEl.textContent = "Notificacoes ativadas!";
            setTimeout(() => modal.hide(), 900);
        } else {
            statusEl.textContent = "Falha ao salvar assinatura.";
        }
    });

    btnLater.addEventListener("click", async () => {
        if (skipUrl) {
            await fetch(skipUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                },
            });
        }
        modal.hide();
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    await registerServiceWorker();
    setupPushPrompt();
});
