import { useState } from 'react';
import { Dices } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { isAuthRedirectPending } from '../lib/authRedirect';

export default function LoginPage() {
  const { signInWithGoogle, firebaseReady, signInError, loading } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const returning = isAuthRedirectPending();
  const message = error || signInError;

  const signIn = async () => {
    setError(null);
    setBusy(true);
    try {
      await signInWithGoogle();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed.');
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="panel-glow w-full max-w-md p-8 space-y-6 text-center">
        <div className="flex justify-center text-accent">
          <Dices size={36} />
        </div>
        <div className="space-y-2">
          <h1 className="font-display text-3xl font-semibold text-gradient">Auto-DM</h1>
          <p className="text-sm text-muted">
            Sign in with Google to continue. Only the allowed account can open this app.
          </p>
        </div>
        <button
          type="button"
          className="btn-primary w-full"
          onClick={() => void signIn()}
          disabled={busy || returning || loading || !firebaseReady}
        >
          {busy || returning || loading ? 'Signing in…' : 'Continue with Google'}
        </button>
        {!firebaseReady && <p className="text-sm text-danger">Firebase is not configured on this build.</p>}
        {message && <p className="text-sm text-danger">{message}</p>}
      </div>
    </div>
  );
}
