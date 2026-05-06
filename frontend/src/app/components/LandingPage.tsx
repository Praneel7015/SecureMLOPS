import { Shield, ChevronRight, Lock, Zap, Server } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { Button } from './ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';

interface LandingPageProps {
  onNavigateLogin: () => void;
}

export function LandingPage({ onNavigateLogin }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      {/* Header */}
      <header className="px-6 py-4 flex items-center justify-between border-b border-border bg-card">
          <div className="flex items-center gap-2">
          <Shield className="w-8 h-8 text-accent" />
          <span className="font-mono text-xl font-bold tracking-tight">Axion</span>
        </div>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <Button onClick={onNavigateLogin} size="sm" className="font-medium shadow-sm">
            Sign In
          </Button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24 bg-gradient-to-b from-background to-card/50">
        <div className="max-w-4xl space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-balance text-foreground leading-[1.1]">
            Enterprise-Grade <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-accent/60">
              AI Model Security
            </span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Protect your machine learning pipelines with rigorous data integrity checks,
            advanced anomaly detection, and automated threat mitigation.
          </p>
          <div className="pt-8 space-x-4">
            <Button
              onClick={onNavigateLogin}
              size="lg"
              className="gap-2 shadow-lg"
            >
              Get Started <ChevronRight className="w-5 h-5" />
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => {
                const features = document.getElementById('features');
                if (features) {
                  features.scrollIntoView({ behavior: 'smooth' });
                }
              }}
            >
              Learn More
            </Button>
          </div>
        </div>
      </main>

      {/* Features Grid */}
      <section id="features" className="py-24 bg-card border-t border-border">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="bg-background">
              <CardHeader className="space-y-4 pb-4">
                <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center">
                  <Lock className="w-6 h-6 text-accent" />
                </div>
                <CardTitle className="text-xl">Data Integrity</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-base leading-relaxed">
                  Ensure provenance and integrity of datasets and models. Detect
                  tampering before deployment.
                </CardDescription>
              </CardContent>
            </Card>

            <Card className="bg-background">
              <CardHeader className="space-y-4 pb-4">
                <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-accent" />
                </div>
                <CardTitle className="text-xl">Anomaly Detection</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-base leading-relaxed">
                  Real-time scanning for adversarial attacks and unexpected model behavior
                  during inference.
                </CardDescription>
              </CardContent>
            </Card>

            <Card className="bg-background">
              <CardHeader className="space-y-4 pb-4">
                <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center">
                  <Server className="w-6 h-6 text-accent" />
                </div>
                <CardTitle className="text-xl">Centralized Auditing</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-base leading-relaxed">
                  Comprehensive audit logs and reporting for compliance, tracking every
                  change to your ML assets.
                </CardDescription>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
      
      <footer className="border-t border-border py-8 text-center bg-background">
        <p className="text-sm text-muted-foreground font-mono">
          &copy; {new Date().getFullYear()} Axion. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
