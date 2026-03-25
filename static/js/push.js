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

async function enablePushFlow(publicKey, subscribeUrl, statusEl) {
    if (!publicKey || !subscribeUrl || !("Notification" in window)) return false;

    if (Notification.permission === "denied") {
        if (statusEl) {
            statusEl.textContent = "Permissao negada. Ative nas configuracoes do navegador.";
        }
        return false;
    }

    if (statusEl) statusEl.textContent = "Preparando notificacoes...";
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
        if (statusEl) {
            statusEl.textContent = "Permissao negada. Voce pode ativar depois no navegador.";
        }
        return false;
    }

    const registration = await registerServiceWorker();
    if (!registration) {
        if (statusEl) statusEl.textContent = "Nao foi possivel registrar o service worker.";
        return false;
    }

    const sub = await subscribeToPush(registration, publicKey);
    if (!sub) {
        if (statusEl) statusEl.textContent = "Falha ao criar assinatura.";
        return false;
    }

    const ok = await sendSubscription(sub, subscribeUrl);
    if (!ok) {
        if (statusEl) statusEl.textContent = "Falha ao salvar assinatura.";
        return false;
    }

    if (statusEl) statusEl.textContent = "Notificacoes ativadas!";
    return true;
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
        const ok = await enablePushFlow(publicKey, subscribeUrl, statusEl);
        if (ok) {
            setTimeout(() => modal.hide(), 900);
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

function setupPushEnableButtons() {
    const modalEl = document.getElementById("pushPromptModal");
    if (!modalEl) return;
    const publicKey = modalEl.getAttribute("data-public-key") || "";
    const subscribeUrl = modalEl.getAttribute("data-subscribe-url") || "";
    if (!publicKey || !subscribeUrl) return;

    window.caronasPushEnable = async () => {
        return enablePushFlow(publicKey, subscribeUrl, null);
    };
}

document.addEventListener("DOMContentLoaded", async () => {
    await registerServiceWorker();
    setupPushPrompt();
    setupPushEnableButtons();

    const toast = document.getElementById("pushToast");
    const toastTitle = document.getElementById("pushToastTitle");
    const toastBody = document.getElementById("pushToastBody");
    const toastClose = document.getElementById("pushToastClose");
    let toastTimer = null;

    function showToast(title, body) {
        if (!toast || !toastTitle || !toastBody) return;
        if (!window.matchMedia("(max-width: 575.98px)").matches) return;
        toastTitle.textContent = title || "Nova notificacao";
        toastBody.textContent = body || "";
        toast.classList.add("show");
        if (toastTimer) clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.remove("show"), 4500);
    }

    if (toastClose) {
        toastClose.addEventListener("click", () => {
            toast.classList.remove("show");
        });
    }

    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.addEventListener("message", (event) => {
            if (!event.data || event.data.type !== "push") return;
            showToast(event.data.title, event.data.body);
        });
    }
});
