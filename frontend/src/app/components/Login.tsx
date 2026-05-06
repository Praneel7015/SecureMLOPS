import { Shield, ArrowLeft } from 'lucide-react';
import { useState, type ChangeEvent, type FormEvent } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';

interface LoginProps {
  onLogin: (username: string, password: string) => Promise<{ success: boolean; message?: string }>;
  onBack: () => void;
}

export function Login({ onLogin, onBack }: LoginProps) {
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
      <Card className="w-full max-w-md relative">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="absolute top-4 left-4"
          aria-label="Back to landing page"
        >
          <ArrowLeft className="w-5 h-5 text-muted-foreground" />
        </Button>
          <CardHeader className="flex flex-col items-center mt-8">
          <div className="w-16 h-16 rounded-full bg-accent flex items-center justify-center mb-4">
            <Shield className="w-8 h-8 text-accent-foreground" />
          </div>
          <CardTitle>Axion</CardTitle>
          <CardDescription>AI Model Security Analysis</CardDescription>
        </CardHeader>

        <CardContent>
          <form action="/login" method="post" onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                type="text"
                id="username"
                name="username"
                value={username}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                type="password"
                id="password"
                name="password"
                value={password}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
              />
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>

            {error && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-destructive">
                {error}
              </div>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
