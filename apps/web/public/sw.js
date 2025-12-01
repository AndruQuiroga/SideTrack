self.addEventListener('install', () => {
  // Activate immediately on install
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// Placeholder: pass-through fetch; can be extended to cache assets
self.addEventListener('fetch', () => {});
