import { Shield } from 'lucide-react';
import { useState, type ChangeEvent, type FormEvent } from 'react';

interface LoginProps {
  onLogin: (username: string, password: string) => Promise<{ success: boolean; message?: string }>;
}

export function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await onLogin(username, password);
      if (!result.success) {
        setError(result.message || 'Authentication failed.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="auth-card w-full max-w-md bg-card rounded-lg border border-border p-8 shadow-lg">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-full bg-accent flex items-center justify-center mb-4">
            <Shield className="w-8 h-8 text-accent-foreground" />
          </div>
          <h1 className="text-foreground">SecureMLOPS</h1>
          <p className="text-muted-foreground mt-1">AI Model Security Analysis</p>
        </div>

        <form action="/login" method="post" onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block mb-2 text-foreground">
              Username
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={username}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
              placeholder="Enter your username"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="block mb-2 text-foreground">
              Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={password}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
              placeholder="Enter your password"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-accent hover:bg-accent-600 disabled:bg-muted disabled:text-muted-foreground text-accent-foreground py-3 rounded-lg transition-colors"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>

          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-destructive">
              {error}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
