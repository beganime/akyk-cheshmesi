const CACHE_NAME = "akyl-web-v7";
const STATIC_PATHS = [
  "/",
  "/login/",
  "/messenger/",
  "/privacy/",
  "/terms/",
  "/support/",
  "/styles.css?v=8",
  "/site.css",
  "/landing-extra.css",
  "/doppler.css?v=8",
  "/site.js",
  "/app.js?v=8",
  "/storage.js?v=8",
  "/sphere.js",
  "/vendor/three.min.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => Promise.all(
      STATIC_PATHS.map((path) => cache.add(path).catch(() => null))
    )).then(() => self.skipWaiting())
  );
});

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (error) {
    payload = { title: "Akyl Cheshmesi", body: event.data ? event.data.text() : "Новое событие" };
  }

  const data = payload.data || {};
  const isCall = ["call", "incoming_call"].includes(data.type);
  event.waitUntil(self.registration.showNotification(payload.title || "Akyl Cheshmesi", {
    body: payload.body || "Новое событие",
    icon: "/assets/akyl_logo.png",
    badge: "/assets/akyl_logo.png",
    tag: payload.tag || `${data.type || "message"}:${data.call_uuid || data.message_uuid || data.chat_uuid || "new"}`,
    renotify: isCall,
    requireInteraction: isCall,
    data: { ...data, url: payload.url || "/messenger/" },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/messenger/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then(async (windows) => {
      const target = new URL(targetUrl, self.location.origin);
      for (const client of windows) {
        if (new URL(client.url).origin === target.origin) {
          await client.focus();
          if ("navigate" in client) await client.navigate(target.href);
          return;
        }
      }
      return clients.openWindow(target.href);
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (/^\/(api|admin|ws|media|_protected_media)\//.test(url.pathname)) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      }).catch(() => caches.match(request).then((cached) => cached || caches.match(url.pathname)))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      }).catch(() => null);
      if (cached) {
        event.waitUntil(network);
        return cached;
      }
      return network.then((response) => {
        if (response) return response;
        if (request.mode === "navigate") return caches.match("/");
        return Response.error();
      });
    })
  );
});
