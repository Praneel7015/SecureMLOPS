import { useState, type FormEvent } from 'react';
import { AlertCircle, ArrowRight, Check } from 'lucide-react';
import { AuthLayout, AuthField, AuthDivider, GoogleButton } from './auth/AuthLayout';

interface SignupProps {
  onSignup: (payload: {
    name: string;
    email: string;
    password: string;
  }) => Promise<{ success: boolean; message?: string }>;
  onNavigateLogin: () => void;
  onNavigateHome: () => void;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function Signup({ onSignup, onNavigateLogin, onNavigateHome }: SignupProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const rules = [
    { ok: password.length >= 8, label: 'At least 8 characters' },
    { ok: /[A-Z]/.test(password) && /[a-z]/.test(password), label: 'Upper & lowercase' },
    { ok: /\d/.test(password), label: 'A number' },
  ];

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) return setError('Please enter your name.');
    if (!EMAIL_RE.test(email)) return setError('Please enter a valid email address.');
    if (!rules.every((r) => r.ok)) return setError('Please meet all password requirements.');

    setIsLoading(true);
    try {
      const result = await onSignup({ name: name.trim(), email: email.trim(), password });
      if (!result.success) setError(result.message || 'Could not create your account.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Create account"
      title="Start securing your models."
      subtitle="Create your Echelon console in under a minute."
      onNavigateHome={onNavigateHome}
    >
      <div className="space-y-5">
        <GoogleButton label="Sign up with Google" />
        <AuthDivider />

        <form onSubmit={handleSubmit} className="space-y-4">
          <AuthField
            label="Full name"
            id="name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ada Lovelace"
            required
          />
          <AuthField
            label="Work email"
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            required
          />
          <AuthField
            label="Password"
            id="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Create a strong password"
            required
          />

          {password.length > 0 && (
            <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-3">
              {rules.map((r) => (
                <li
                  key={r.label}
                  className={`flex items-center gap-1.5 text-xs transition-colors ${
                    r.ok ? 'text-success' : 'text-muted-foreground/60'
                  }`}
                >
                  <Check className={`h-3.5 w-3.5 ${r.ok ? 'opacity-100' : 'opacity-40'}`} />
                  {r.label}
                </li>
              ))}
            </ul>
          )}

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
            {isLoading ? 'Creating account…' : 'Create account'}
            {!isLoading && (
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            )}
          </button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <button
            onClick={onNavigateLogin}
            className="font-medium text-foreground underline decoration-accent decoration-2 underline-offset-4 transition-colors hover:text-accent"
          >
            Sign in
          </button>
        </p>

        <p className="text-center text-xs leading-relaxed text-muted-foreground/60">
          By creating an account you agree to Echelon's Terms and acknowledge our
          Privacy Policy.
        </p>
      </div>
    </AuthLayout>
  );
}
