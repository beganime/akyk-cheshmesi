const CACHE_NAME = "akyl-web-v3";
const STATIC_PATHS = [
  "/",
  "/login/",
  "/messenger/",
  "/privacy/",
  "/terms/",
  "/support/",
  "/styles.css",
  "/site.css",
  "/landing-extra.css",
  "/doppler.css",
  "/site.js",
  "/app.js",
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
