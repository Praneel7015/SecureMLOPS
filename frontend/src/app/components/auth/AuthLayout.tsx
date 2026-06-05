import { type InputHTMLAttributes, type ReactNode, forwardRef } from 'react';
import { ArrowLeft } from 'lucide-react';
import { motion } from 'motion/react';
import { Wordmark, EchelonMark } from '../brand/Wordmark';
import { ThemeToggle } from '../ThemeToggle';
import { cn } from '../ui/utils';

interface AuthLayoutProps {
  eyebrow: string;
  title: ReactNode;
  subtitle: string;
  children: ReactNode;
  onNavigateHome: () => void;
}

/**
 * Shared editorial split-screen for Login + Signup.
 * Left: a static obsidian brand panel (consistent in both themes).
 * Right: theme-aware form column.
 */
export function AuthLayout({
  eyebrow,
  title,
  subtitle,
  children,
  onNavigateHome,
}: AuthLayoutProps) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      {/* Brand panel — always obsidian */}
      <aside className="relative hidden overflow-hidden bg-[#0A0A0B] text-[#F4F4F1] lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="grid-lines pointer-events-none absolute inset-0 opacity-[0.4] [mask-image:radial-gradient(ellipse_at_center,black,transparent_80%)]" />
        <button
          onClick={onNavigateHome}
          className="relative z-10 inline-flex items-center gap-2.5 text-left"
        >
          <EchelonMark className="h-7 w-7" />
          <span className="font-display text-xl font-semibold tracking-tight">Echelon</span>
        </button>

        <div className="relative z-10 max-w-md">
          <span className="eyebrow text-[#F4F4F1]/50">Security for machine intelligence</span>
          <p className="mt-6 font-display text-4xl font-semibold leading-[1.05] tracking-[-0.03em]">
            Every model decision,{' '}
            <span className="text-accent">verified and recorded.</span>
          </p>
        </div>

        <div className="relative z-10 space-y-3 font-mono text-xs text-[#F4F4F1]/50">
          {[
            ['integrity', 'verified', true],
            ['anomaly', 'scanning', true],
            ['audit', 'streaming', true],
          ].map(([k, v]) => (
            <div key={k as string} className="flex items-center gap-3">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              <span className="w-24 uppercase tracking-[0.18em]">{k}</span>
              <span className="text-[#F4F4F1]/70">{v}</span>
            </div>
          ))}
        </div>
      </aside>

      {/* Form column */}
      <main className="relative flex flex-col bg-background px-6 py-8 sm:px-10 lg:px-16">
        <div className="flex items-center justify-between">
          <button
            onClick={onNavigateHome}
            className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <div className="flex items-center gap-3">
            <span className="lg:hidden">
              <Wordmark size="sm" />
            </span>
            <ThemeToggle />
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-1 flex-col justify-center py-10"
        >
          <div className="mx-auto w-full max-w-sm">
            <span className="eyebrow text-accent">{eyebrow}</span>
            <h1 className="mt-4 font-display text-4xl font-semibold leading-[1.05] tracking-[-0.03em] text-foreground">
              {title}
            </h1>
            <p className="mt-3 text-muted-foreground">{subtitle}</p>
            <div className="mt-8">{children}</div>
          </div>
        </motion.div>
      </main>
    </div>
  );
}

/* ── Reusable form primitives ───────────────────────────────────────────── */

interface AuthFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export const AuthField = forwardRef<HTMLInputElement, AuthFieldProps>(
  ({ label, id, className, ...props }, ref) => (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
      </label>
      <input
        ref={ref}
        id={id}
        className={cn(
          'w-full rounded-lg border border-input bg-input-background px-4 py-3 text-foreground transition',
          'placeholder:text-muted-foreground/50',
          'focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25',
          className,
        )}
        {...props}
      />
    </div>
  ),
);
AuthField.displayName = 'AuthField';

export function AuthDivider({ label = 'or' }: { label?: string }) {
  return (
    <div className="flex items-center gap-4 py-1">
      <span className="h-px flex-1 bg-border" />
      <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground/60">
        {label}
      </span>
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}

export function GoogleButton({ label }: { label: string }) {
  return (
    <button
      type="button"
      onClick={() => {
        window.location.href = '/auth/google';
      }}
      className="flex w-full items-center justify-center gap-3 rounded-lg border border-input bg-card px-4 py-3 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
    >
      <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1Z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.3 9.14 5.38 12 5.38Z"
        />
      </svg>
      {label}
    </button>
  );
}
