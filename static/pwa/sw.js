// Очень простой SW: кэшируем статику. Видео обычно не кэшируют целиком.
const CACHE = "mz-video-v1";
const ASSETS = [
  "/mini-player/",
  "/static/pwa/manifest.webmanifest",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  // Для навигации: отдаём кэш/сеть
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req).catch(() => caches.match("/mini-player/"))
    );
    return;
  }
  // Статика: cache-first
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req))
  );
});