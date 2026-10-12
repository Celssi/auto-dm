const REDIRECT_FLAG = 'auto-dm:auth-redirect';

export function isLocalHost(hostname = window.location.hostname): boolean {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]';
}

export function isLocalDevAuth(): boolean {
  return import.meta.env.DEV && typeof window !== 'undefined' && isLocalHost();
}

export function markAuthRedirect(): void {
  try {
    sessionStorage.setItem(REDIRECT_FLAG, '1');
  } catch {
    /* private mode */
  }
}

export function clearAuthRedirect(): void {
  try {
    sessionStorage.removeItem(REDIRECT_FLAG);
  } catch {
    /* private mode */
  }
}

export function isAuthRedirectPending(): boolean {
  try {
    return sessionStorage.getItem(REDIRECT_FLAG) === '1';
  } catch {
    return false;
  }
}
