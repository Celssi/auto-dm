import { createContext, use, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  getRedirectResult,
  onAuthStateChanged,
  signInWithRedirect,
  signOut as firebaseSignOut,
  type User,
} from 'firebase/auth';
import { ALLOWED_EMAILS, auth, firebaseReady, googleProvider, isAllowedEmail } from '../lib/firebase';
import { setAuthTokenProvider } from '../lib/authToken';
import { clearAuthRedirect, markAuthRedirect } from '../lib/authRedirect';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  firebaseReady: boolean;
  signInError: string | null;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  isAllowedUser: (email: string | null) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function authErrorMessage(error: unknown): string {
  const code = error && typeof error === 'object' && 'code' in error ? String(error.code) : '';
  if (code === 'auth/popup-closed-by-user' || code === 'auth/cancelled-popup-request') {
    return 'Sign-in was interrupted. Try Continue with Google again.';
  }
  if (error instanceof Error && error.message) return error.message;
  return 'Sign-in failed.';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => Boolean(auth));
  const [signInError, setSignInError] = useState<string | null>(null);

  const isAllowedUser = useCallback((email: string | null): boolean => {
    return isAllowedEmail(email);
  }, []);

  useEffect(() => {
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
  }, [isAllowedUser]);

  const signInWithGoogle = useCallback(async () => {
    if (!auth) {
      throw new Error('Firebase is not configured.');
    }
    setSignInError(null);
    markAuthRedirect();
    await signInWithRedirect(auth, googleProvider);
  }, []);

  const signOut = useCallback(async () => {
    if (!auth) return;
    await firebaseSignOut(auth);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      firebaseReady,
      signInError,
      signInWithGoogle,
      signOut,
      isAllowedUser,
    }),
    [user, loading, signInError, signInWithGoogle, signOut, isAllowedUser],
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
