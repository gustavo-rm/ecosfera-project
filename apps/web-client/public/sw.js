/*
 * ECOSFERA service worker: caches the application shell and the fixtures so a planet already loaded keeps working
 * without a connection (RNF-021). There is NO synchronization and no background upload: see docs/frontend/adr/0006.
 * Everything is same-origin; nothing is fetched from third parties.
 */
const VERSION = "ecosfera-shell-v1";
const SHELL = ["/", "/jogo", "/jogo/genese", "/jogo/codex", "/jogo/pesquisa", "/jogo/missoes", "/jogo/dados", "/configuracoes", "/manifest.webmanifest", "/icons/icon.svg", "/fixtures/terra-nivel3.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => Promise.allSettled(SHELL.map((url) => cache.add(url)))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (event) => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  const immutable = url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/fixtures/") || url.pathname.startsWith("/icons/");
  if (immutable) {
    // Cache first: hashed build assets and fixtures never change under the same URL.
    event.respondWith(caches.match(request).then((hit) => hit || fetch(request).then((response) => { const copy = response.clone(); caches.open(VERSION).then((c) => c.put(request, copy)); return response; })));
    return;
  }
  // Network first for pages and data, falling back to the cached copy when offline.
  event.respondWith(fetch(request).then((response) => { if (response.ok) { const copy = response.clone(); caches.open(VERSION).then((c) => c.put(request, copy)); } return response; }).catch(() => caches.match(request).then((hit) => hit || caches.match("/"))));
});
