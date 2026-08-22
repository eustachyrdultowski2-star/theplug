/* The Plug — service worker.
   Shell is cached so the app opens instantly and survives a dead connection;
   API calls and shop images always go to the network. */
const CACHE = "plug-20260823002001";
const SHARE = "plug-share";        // one slot, for the image being handed over
const SHARE_KEY = "/__shared-image";
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

  // Shared straight from TikTok (or any app) through the system share sheet.
  // A screenshot is parked in its own cache and the app is told to come and
  // get it; a shared link only needs to survive the redirect.
  if (e.request.method === "POST" && url.pathname === "/share") {
    e.respondWith((async () => {
      let form;
      try { form = await e.request.formData(); }
      catch (err) { return Response.redirect("/", 303); }

      const file = form.get("image");
      if (file && file.size) {
        const c = await caches.open(SHARE);
        await c.put(SHARE_KEY, new Response(file, {
          headers: { "Content-Type": file.type || "image/jpeg" }
        }));
        return Response.redirect("/?shared=photo", 303);
      }

      const said = [form.get("url"), form.get("text"), form.get("title")]
        .filter(Boolean).join(" ");
      const link = (said.match(/https?:\/\/\S+/) || [""])[0];
      return Response.redirect("/?shared=link&u=" + encodeURIComponent(link), 303);
    })());
    return;
  }

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
