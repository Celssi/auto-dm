const REDIRECT_FLAG = 'auto-dm:auth-redirect';

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
