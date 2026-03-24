self.addEventListener("push", function (event) {
    let data = {};
    try {
        data = event.data ? event.data.json() : {};
    } catch (e) {
        data = {};
    }

    const title = data.title || "Caronas JP";
    const options = {
        body: data.body || "Voce tem uma nova notificacao.",
        icon: "/static/img/caronasjp.png",
        badge: "/static/img/caronasjp.png",
        vibrate: [200, 100, 200],
        tag: "caronasjp",
        renotify: true,
        requireInteraction: true,
        silent: false,
        actions: [
            { action: "open", title: "Abrir" },
            { action: "close", title: "Fechar" },
        ],
        data: {
            url: data.url || "/",
        },
    };

    event.waitUntil(self.registration.showNotification(title, options));

    event.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clientList) {
            for (const client of clientList) {
                client.postMessage({
                    type: "push",
                    title: title,
                    body: options.body,
                    url: options.data.url,
                });
            }
        })
    );
});

self.addEventListener("notificationclick", function (event) {
    event.notification.close();
    if (event.action === "close") {
        return;
    }
    const url = event.notification.data && event.notification.data.url ? event.notification.data.url : "/";
    event.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clientList) {
            for (const client of clientList) {
                if (client.url === url && "focus" in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});
