const RELOAD_FLAG = 'pwa-forced-reload';
const UPDATE_CHECK_MS = 5 * 60 * 1000;

type WatcherWindow = Window & { __pwaUpdateWatcher?: boolean };

export function shouldForcePwaUpdate(): boolean {
  const ua = navigator.userAgent;
  const phone = /iPhone|iPod/.test(ua) || (/Android/i.test(ua) && /Mobile/i.test(ua));
  const narrowTouch = window.matchMedia('(max-width: 767px)').matches && window.matchMedia('(pointer: coarse)').matches;
  const standalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true;
  const touch = navigator.maxTouchPoints > 0 || window.matchMedia('(pointer: coarse)').matches;
  return phone || narrowTouch || (standalone && touch);
}

function reloadOnce() {
  try {
    if (sessionStorage.getItem(RELOAD_FLAG) === '1') return;
    sessionStorage.setItem(RELOAD_FLAG, '1');
  } catch {
    // Private mode can block sessionStorage. The caller still reloads once.
  }
  window.location.reload();
}

function clearReloadFlagLater() {
  window.setTimeout(() => {
    try {
      sessionStorage.removeItem(RELOAD_FLAG);
    } catch {
      // Ignore storage failures.
    }
  }, 15000);
}

export function startPwaUpdates(options: { prompt?: string; registerWorker?: boolean } = {}) {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;
  const watcherWindow = window as WatcherWindow;
  if (watcherWindow.__pwaUpdateWatcher) return;
  watcherWindow.__pwaUpdateWatcher = true;

  const force = shouldForcePwaUpdate();
  const hadController = Boolean(navigator.serviceWorker.controller);
  let reloading = false;

  clearReloadFlagLater();

  if (force && hadController) {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (reloading) return;
      reloading = true;
      reloadOnce();
    });
  }

  const onInstalled = (worker: ServiceWorker) => {
    if (!navigator.serviceWorker.controller) return;
    if (force) {
      worker.postMessage({ type: 'SKIP_WAITING' });
      return;
    }
    if (!options.prompt || !window.confirm(options.prompt)) return;
    worker.postMessage({ type: 'SKIP_WAITING' });
    window.location.reload();
  };

  const watchWorker = (worker: ServiceWorker | null) => {
    if (!worker) return;
    if (worker.state === 'installed') {
      onInstalled(worker);
      return;
    }
    worker.addEventListener('statechange', () => {
      if (worker.state === 'installed') onInstalled(worker);
    });
  };

  const bind = (registration: ServiceWorkerRegistration) => {
    watchWorker(registration.installing);
    watchWorker(registration.waiting);

    registration.addEventListener('updatefound', () => {
      watchWorker(registration.installing);
    });

    const check = () => {
      if (document.visibilityState === 'hidden') return;
      void registration.update().catch(() => undefined);
    };

    document.addEventListener('visibilitychange', check);
    window.addEventListener('focus', check);
    window.setInterval(check, UPDATE_CHECK_MS);
    check();
  };

  if (options.registerWorker === false) {
    void navigator.serviceWorker.ready.then(bind).catch(() => undefined);
    return;
  }

  void navigator.serviceWorker
    .register('/sw.js', { scope: '/' })
    .then(bind)
    .catch(() => undefined);
}
