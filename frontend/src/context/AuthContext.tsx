import {
  createContext,
  use,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { onAuthStateChanged, signInWithPopup, signOut as firebaseSignOut, type User } from 'firebase/auth';
import { ALLOWED_EMAILS, auth, firebaseReady, googleProvider, isAllowedEmail } from '../lib/firebase';
import { setAuthTokenProvider } from '../lib/authToken';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  firebaseReady: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  isAllowedUser: (email: string | null) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const isAllowedUser = useCallback((email: string | null): boolean => {
    return isAllowedEmail(email);
  }, []);

  useEffect(() => {
    if (!auth) {
      setLoading(false);
      return;
    }

    const firebaseAuth = auth;
    setAuthTokenProvider(async () => {
      if (!firebaseAuth.currentUser) return null;
      return firebaseAuth.currentUser.getIdToken();
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
      unsubscribe();
      setAuthTokenProvider(null);
    };
  }, [isAllowedUser]);

  const signInWithGoogle = useCallback(async () => {
    if (!auth) {
      throw new Error('Firebase is not configured.');
    }
    const result = await signInWithPopup(auth, googleProvider);
    if (!isAllowedUser(result.user.email)) {
      await firebaseSignOut(auth);
      throw new Error(`Access denied. Only ${ALLOWED_EMAILS.join(', ')} may sign in.`);
    }
  }, [isAllowedUser]);

  const signOut = useCallback(async () => {
    if (!auth) return;
    await firebaseSignOut(auth);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      firebaseReady,
      signInWithGoogle,
      signOut,
      isAllowedUser,
    }),
    [user, loading, signInWithGoogle, signOut, isAllowedUser],
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
