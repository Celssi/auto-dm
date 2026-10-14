export function authErrorCode(error: unknown): string {
  return error && typeof error === 'object' && 'code' in error ? String(error.code) : '';
}

export function authErrorMessage(error: unknown): string {
  const code = authErrorCode(error);
  if (code === 'auth/popup-closed-by-user' || code === 'auth/cancelled-popup-request') {
    return 'Sign-in was interrupted. Try Continue with Google again.';
  }
  if (code === 'auth/popup-blocked') {
    return 'The browser blocked the Google sign-in window. Allow popups, or try again.';
  }
  if (code === 'auth/unauthorized-domain') {
    return 'This domain is not authorized for Google sign-in.';
  }
  if (code === 'auth/network-request-failed') {
    return 'Could not reach Google sign-in. Check your connection and try again.';
  }
  if (code === 'auth/web-storage-unsupported') {
    return 'This browser is blocking sign-in storage. Allow cookies and try again.';
  }
  if (
    code === 'auth/missing-pending-credential' ||
    code === 'auth/missing-or-invalid-nonce' ||
    code === 'auth/internal-error' ||
    code === 'auth/argument-error'
  ) {
    return 'Sign-in did not complete. Try Continue with Google again.';
  }
  if (code === 'auth/operation-not-allowed') {
    return 'Google sign-in is not enabled for this app.';
  }
  if (error instanceof Error && error.message) {
    const cleaned = error.message
      .replace(/^Firebase:\s*/i, '')
      .replace(/\s*\(auth\/[^)]+\)\.?$/, '')
      .trim();
    if (cleaned && !/^error$/i.test(cleaned)) return cleaned;
  }
  return 'Sign-in failed. Try Continue with Google again.';
}

export function accessDeniedMessage(allowedEmails: string[]): string {
  if (allowedEmails.length === 1) {
    return `Access denied. Only ${allowedEmails[0]} can open this app.`;
  }
  return `Access denied. Only these accounts can open this app: ${allowedEmails.join(', ')}.`;
}
