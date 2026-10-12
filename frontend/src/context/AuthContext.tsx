import { createContext, use, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  getRedirectResult,
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  signOut as firebaseSignOut,
} from 'firebase/auth';
import { ALLOWED_EMAILS, auth, firebaseReady, googleProvider, isAllowedEmail } from '../lib/firebase';
import { setAuthTokenProvider } from '../lib/authToken';
import { clearAuthRedirect, isLocalDevAuth, isLocalHost, markAuthRedirect } from '../lib/authRedirect';

export interface AuthUser {
  email: string | null;
}

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  firebaseReady: boolean;
  signInError: string | null;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  isAllowedUser: (email: string | null) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const localDevUser: AuthUser = { email: ALLOWED_EMAILS[0] ?? 'lauri.mukkala.fi@gmail.com' };

function authErrorCode(error: unknown): string {
  return error && typeof error === 'object' && 'code' in error ? String(error.code) : '';
}

function authErrorMessage(error: unknown): string {
  const code = authErrorCode(error);
  if (code === 'auth/popup-closed-by-user' || code === 'auth/cancelled-popup-request') {
    return 'Sign-in was interrupted. Try Continue with Google again.';
  }
  if (code === 'auth/unauthorized-domain') {
    return 'This domain is not authorized for Google sign-in.';
  }
  if (error instanceof Error && error.message) return error.message;
  return 'Sign-in failed.';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const localDev = isLocalDevAuth();
  const [user, setUser] = useState<AuthUser | null>(() => (localDev ? localDevUser : null));
  const [loading, setLoading] = useState(() => !localDev && Boolean(auth));
  const [signInError, setSignInError] = useState<string | null>(null);

  const isAllowedUser = useCallback((email: string | null): boolean => {
    return isAllowedEmail(email);
  }, []);

  useEffect(() => {
    if (localDev) {
      setAuthTokenProvider(async () => null);
      return () => setAuthTokenProvider(null);
    }
    if (!auth) return;

    const firebaseAuth = auth;
    setAuthTokenProvider(async () => {
      if (!firebaseAuth.currentUser) return null;
      return firebaseAuth.currentUser.getIdToken();
    });

    let cancelled = false;

    void getRedirectResult(firebaseAuth)
      .then(async (result) => {
        clearAuthRedirect();
        if (result?.user && !isAllowedUser(result.user.email)) {
          await firebaseSignOut(firebaseAuth);
          if (!cancelled) {
            setSignInError(`Access denied. Only ${ALLOWED_EMAILS.join(', ')} may sign in.`);
          }
        }
      })
      .catch((error: unknown) => {
        clearAuthRedirect();
        if (!cancelled) setSignInError(authErrorMessage(error));
      });

    const unsubscribe = onAuthStateChanged(firebaseAuth, async (firebaseUser) => {
      if (firebaseUser && !isAllowedUser(firebaseUser.email)) {
        await firebaseSignOut(firebaseAuth);
        setUser(null);
        setLoading(false);
        return;
      }
      setUser(firebaseUser);
      setLoading(false);
    });

    return () => {
      cancelled = true;
      unsubscribe();
      setAuthTokenProvider(null);
    };
  }, [isAllowedUser, localDev]);

  const signInWithGoogle = useCallback(async () => {
    if (localDev) return;
    if (!auth) {
      throw new Error('Firebase is not configured.');
    }
    setSignInError(null);

    if (isLocalHost()) {
      try {
        const result = await signInWithPopup(auth, googleProvider);
        if (result.user && !isAllowedUser(result.user.email)) {
          await firebaseSignOut(auth);
          throw new Error(`Access denied. Only ${ALLOWED_EMAILS.join(', ')} may sign in.`);
        }
        return;
      } catch (error) {
        const code = authErrorCode(error);
        if (code !== 'auth/popup-blocked' && code !== 'auth/cancelled-popup-request') {
          throw error;
        }
      }
    }

    markAuthRedirect();
    await signInWithRedirect(auth, googleProvider);
  }, [isAllowedUser, localDev]);

  const signOut = useCallback(async () => {
    if (localDev || !auth) return;
    await firebaseSignOut(auth);
  }, [localDev]);

  const value = useMemo(
    () => ({
      user,
      loading,
      firebaseReady: localDev || firebaseReady,
      signInError,
      signInWithGoogle,
      signOut,
      isAllowedUser,
    }),
    [user, loading, localDev, signInError, signInWithGoogle, signOut, isAllowedUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = use(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
