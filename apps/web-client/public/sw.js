/*
 * ECOSFERA service worker: caches the application shell and the fixtures so a planet already loaded keeps working
 * without a connection (RNF-021). There is NO synchronization and no background upload: see docs/frontend/adr/0006.
 * Everything is same-origin; nothing is fetched from third parties.
 *
 * What is cached, on purpose narrow:
 *   - hashed build assets (/_next/static/): cache first, they never change under the same URL;
 *   - page navigations of the shell: network first, cached copy when offline;
 *   - fixtures and icons: network first (their URLs are not hashed).
 * Nothing else is stored. In particular, no API or data response will ever be cached here: when a backend exists,
 * authenticated responses must not persist on a shared school device.
 */
const VERSION = "ecosfera-shell-v3";
const SHELL = ["/", "/jogo", "/jogo/genese", "/jogo/codex", "/jogo/pesquisa", "/jogo/missoes", "/jogo/dados", "/configuracoes", "/manifest.webmanifest", "/icons/icon.svg", "/fixtures/terra-nivel3.json"];

const put = (request, response) => { if (response.ok && response.type === "basic") { const copy = response.clone(); caches.open(VERSION).then((c) => c.put(request, copy)); } return response; };

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => Promise.allSettled(SHELL.map((url) => fetch(url).then((r) => (r.ok ? cache.put(url, r) : undefined))))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (event) => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(caches.match(request).then((hit) => hit || fetch(request).then((response) => put(request, response))));
    return;
  }
  const shellAsset = url.pathname.startsWith("/fixtures/") || url.pathname.startsWith("/icons/") || url.pathname === "/manifest.webmanifest";
  // Only the student shell is kept for offline use; teacher pages depend on a server and are never stored.
  if ((request.mode === "navigate" && SHELL.includes(url.pathname)) || shellAsset) {
    event.respondWith(fetch(request).then((response) => put(request, response)).catch(() => caches.match(request, { ignoreSearch: true }).then((hit) => hit || (request.mode === "navigate" ? caches.match("/") : Response.error()))));
  }
  // Anything else goes straight to the network and is not stored.
});
