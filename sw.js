/* The Plug — service worker.
   Shell is cached so the app opens instantly and survives a dead connection;
   API calls and shop images always go to the network. */
const CACHE = "plug-v1";
const SHELL = ["/", "/assets/js/catalog.js", "/manifest.webmanifest",
               "/assets/icons/icon-192.png", "/assets/icons/icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.pathname.startsWith("/api/")) return;          // never cache API answers

  // navigations: try the network, fall back to the cached shell
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).catch(() => caches.match("/")));
    return;
  }
  // everything else: cache first, then network
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
    if (res.ok && url.origin === location.origin) {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
    }
    return res;
  }).catch(() => hit)));
});
