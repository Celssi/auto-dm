import { initializeApp } from 'firebase/app';
import { GoogleAuthProvider, getAuth } from 'firebase/auth';
import { isLocalHost } from './authRedirect';

function resolveAuthDomain(configured: string | undefined): string {
  if (typeof window !== 'undefined' && !isLocalHost()) {
    return window.location.hostname;
  }
  return configured || '';
}

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: resolveAuthDomain(import.meta.env.VITE_FIREBASE_AUTH_DOMAIN),
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const firebaseReady = Object.values(firebaseConfig).every(
  (value) => typeof value === 'string' && value.length > 0,
);

const app = firebaseReady ? initializeApp(firebaseConfig) : null;

export const auth = app ? getAuth(app) : null;
export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

const allowedEmailsEnv = import.meta.env.VITE_ALLOWED_EMAILS || '';
export const ALLOWED_EMAILS: string[] = allowedEmailsEnv
  .split(',')
  .map((email) => email.trim())
  .filter(Boolean);

if (ALLOWED_EMAILS.length === 0) {
  ALLOWED_EMAILS.push('lauri.mukkala.fi@gmail.com');
}

export function isAllowedEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const needle = email.trim().toLowerCase();
  return ALLOWED_EMAILS.some((allowed) => allowed.toLowerCase() === needle);
}
