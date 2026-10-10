// Network-first for the page's own files; the cache is only an offline fallback.
// Cross-origin requests (API, S3 PUT, presigned audio/CAM) are never intercepted.
// Bump CACHE_VERSION on every deploy so old caches are dropped.
const CACHE_VERSION = "v4";
const CACHE = `hazebusters-${CACHE_VERSION}`;
const SHELL = ["./", "index.html", "styles.css", "config.js", "format.js", "api.js", "result.js", "app.js",
  "manifest.webmanifest", "icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin || url.pathname.includes("/mock/")) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        if (res.ok) caches.open(CACHE).then((c) => c.put(e.request, res.clone()));
        return res;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true })),
  );
});
