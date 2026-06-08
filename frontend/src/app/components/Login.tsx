import { useState, type FormEvent } from 'react';
import { AlertCircle, ArrowRight } from 'lucide-react';
import { AuthLayout, AuthField, AuthDivider, GoogleButton } from './auth/AuthLayout';

interface LoginProps {
  onLogin: (
    identifier: string,
    password: string,
  ) => Promise<{ success: boolean; message?: string }>;
  onNavigateSignup: () => void;
  onNavigateHome: () => void;
}

export function Login({ onLogin, onNavigateSignup, onNavigateHome }: LoginProps) {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      const result = await onLogin(identifier, password);
      if (!result.success) setError(result.message || 'Authentication failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Console access"
      title="Welcome back."
      subtitle="Sign in to your Echelon security console."
      onNavigateHome={onNavigateHome}
    >
      <div className="space-y-5">
        <GoogleButton label="Continue with Google" />
        <AuthDivider />

        <form onSubmit={handleSubmit} className="space-y-4">
          <AuthField
            label="Email or username"
            id="identifier"
            type="text"
            autoComplete="username"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="you@company.com"
            required
          />
          <AuthField
            label="Password"
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="group flex w-full items-center justify-center gap-2 rounded-lg bg-foreground py-3 text-sm font-medium text-background transition-all hover:opacity-90 disabled:opacity-50"
          >
            {isLoading ? 'Signing in…' : 'Sign in'}
            {!isLoading && (
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            )}
          </button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          New to Echelon?{' '}
          <button
            onClick={onNavigateSignup}
            className="font-medium text-foreground underline decoration-accent decoration-2 underline-offset-4 transition-colors hover:text-accent"
          >
            Create an account
          </button>
        </p>
      </div>
    </AuthLayout>
  );
}
