import { type ReactNode } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import {
  ArrowRight,
  ArrowUpRight,
  Lock,
  Radar,
  ScrollText,
} from 'lucide-react';
import { Wordmark } from './brand/Wordmark';
import { ThemeToggle } from './ThemeToggle';
import { Button } from './ui/button';

interface LandingPageProps {
  onNavigateLogin: () => void;
  onNavigateSignup: () => void;
}

/* ── Motion helper: editorial scroll-reveal ─────────────────────────────── */
function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  // Reduced-motion (or animation failure) must never leave content invisible.
  if (reduce) {
    return <div className={className}>{children}</div>;
  }
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

const PILLARS = [
  {
    n: '01',
    icon: Lock,
    title: 'Data Integrity',
    body:
      'Provenance and integrity for every dataset and model checkpoint. Echelon fingerprints what enters your pipeline and flags tampering before it ever reaches production.',
  },
  {
    n: '02',
    icon: Radar,
    title: 'Anomaly Detection',
    body:
      'Real-time scanning for adversarial inputs, distribution drift, and unexpected model behavior during inference — caught the moment it deviates from baseline.',
  },
  {
    n: '03',
    icon: ScrollText,
    title: 'Centralized Auditing',
    body:
      'An immutable, queryable record of every change to your ML assets. Built for compliance, designed so every decision can be explained and replayed.',
  },
];

const PIPELINE = [
  { k: 'Ingest', d: 'Datasets & models enter the gate' },
  { k: 'Verify', d: 'Integrity & provenance checks' },
  { k: 'Detect', d: 'Anomaly & adversarial scan' },
  { k: 'Decide', d: 'Risk-scored allow / block' },
  { k: 'Audit', d: 'Immutable event written' },
];

const STATS = [
  { v: '99.98%', l: 'Integrity checks passed' },
  { v: '<12ms', l: 'Median inference scan' },
  { v: 'Zero', l: 'Trust assumptions' },
  { v: '24/7', l: 'Continuous drift watch' },
];

export function LandingPage({ onNavigateLogin, onNavigateSignup }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-background text-foreground antialiased">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-10">
          <Wordmark size="md" />
          <div className="flex items-center gap-2 sm:gap-3">
            <ThemeToggle />
            <button
              onClick={onNavigateLogin}
              className="hidden px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground sm:block"
            >
              Sign in
            </button>
            <Button onClick={onNavigateSignup} size="sm" className="font-medium">
              Get started
            </Button>
          </div>
        </div>
      </header>

      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-b border-border">
        <div className="grid-lines pointer-events-none absolute inset-0 opacity-[0.5] [mask-image:radial-gradient(ellipse_at_top,black,transparent_75%)]" />
        <div className="relative mx-auto max-w-7xl px-6 pb-24 pt-20 lg:px-10 lg:pb-32 lg:pt-28">
          <Reveal>
            <div className="flex items-center gap-3">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
              </span>
              <span className="eyebrow text-muted-foreground">
                AI Model Security · System online
              </span>
            </div>
          </Reveal>

          <Reveal delay={0.08}>
            <h1 className="mt-8 max-w-5xl text-balance font-display text-[clamp(2.75rem,8vw,7rem)] font-semibold leading-[0.95] tracking-[-0.04em]">
              Security for
              <br />
              machine{' '}
              <span className="underline decoration-accent decoration-4 underline-offset-[0.12em] lg:decoration-[8px]">
                intelligence
              </span>
              .
            </h1>
          </Reveal>

          <Reveal delay={0.16}>
            <p className="mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground lg:text-xl">
              Echelon guards every stage of the ML lifecycle — verifying data
              provenance, catching adversarial drift in real time, and writing an
              immutable audit trail for everything that touches your models.
            </p>
          </Reveal>

          <Reveal delay={0.24}>
            <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Button onClick={onNavigateSignup} size="lg" className="group gap-2">
                Get started
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Button>
              <Button
                onClick={onNavigateLogin}
                variant="outline"
                size="lg"
                className="gap-2"
              >
                Sign in to console
              </Button>
            </div>
          </Reveal>

          <Reveal delay={0.32}>
            <div className="mt-16 flex flex-wrap items-center gap-x-8 gap-y-3 border-t border-border pt-6">
              {['Zero-trust pipeline', 'SOC2-ready audit', 'On-prem or cloud'].map((t) => (
                <span key={t} className="eyebrow text-muted-foreground/70">
                  {t}
                </span>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Stat band ──────────────────────────────────────────────────── */}
      <section className="border-b border-border">
        <div className="mx-auto grid max-w-7xl grid-cols-2 lg:grid-cols-4">
          {STATS.map((s, i) => (
            <Reveal
              key={s.l}
              delay={i * 0.06}
              className={`border-border p-8 lg:p-10 ${
                i % 2 === 0 ? 'border-r' : ''
              } ${i < 2 ? 'border-b lg:border-b-0' : ''} ${
                i === 2 ? 'lg:border-r' : ''
              } ${i === 1 ? 'lg:border-r' : ''}`}
            >
              <div className="font-mono text-4xl font-medium tracking-tight text-foreground lg:text-5xl">
                {s.v}
              </div>
              <div className="mt-3 text-sm text-muted-foreground">{s.l}</div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── 01 · Capabilities (pillars) ────────────────────────────────── */}
      <section id="features" className="border-b border-border">
        <div className="mx-auto max-w-7xl px-6 py-24 lg:px-10 lg:py-32">
          <Reveal>
            <div className="flex items-baseline gap-4">
              <span className="eyebrow text-accent">01</span>
              <span className="eyebrow text-muted-foreground">Capabilities</span>
            </div>
          </Reveal>
          <Reveal delay={0.06}>
            <h2 className="mt-6 max-w-3xl text-balance font-display text-[clamp(2rem,4.5vw,3.5rem)] font-semibold leading-[1.05] tracking-[-0.03em]">
              Three layers of defense, one control plane.
            </h2>
          </Reveal>

          <div className="mt-16 grid gap-px overflow-hidden border border-border bg-border md:grid-cols-3">
            {PILLARS.map((p, i) => {
              const Icon = p.icon;
              return (
                <Reveal key={p.title} delay={i * 0.1} className="h-full">
                  <div className="group flex h-full flex-col bg-card p-8 transition-colors hover:bg-secondary lg:p-10">
                    <div className="flex items-center justify-between">
                      <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border bg-background text-foreground transition-colors group-hover:border-accent group-hover:text-accent">
                        <Icon className="h-5 w-5" strokeWidth={1.5} />
                      </div>
                      <span className="font-mono text-sm text-muted-foreground/60">{p.n}</span>
                    </div>
                    <h3 className="mt-8 font-display text-2xl font-semibold tracking-tight">
                      {p.title}
                    </h3>
                    <p className="mt-3 flex-1 text-[0.95rem] leading-relaxed text-muted-foreground">
                      {p.body}
                    </p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── 02 · How it works (echelon pipeline) ───────────────────────── */}
      <section className="border-b border-border bg-secondary/40">
        <div className="mx-auto max-w-7xl px-6 py-24 lg:px-10 lg:py-32">
          <Reveal>
            <div className="flex items-baseline gap-4">
              <span className="eyebrow text-accent">02</span>
              <span className="eyebrow text-muted-foreground">The Echelon pipeline</span>
            </div>
          </Reveal>
          <Reveal delay={0.06}>
            <h2 className="mt-6 max-w-3xl text-balance font-display text-[clamp(2rem,4.5vw,3.5rem)] font-semibold leading-[1.05] tracking-[-0.03em]">
              Every asset clears the gate before it ships.
            </h2>
          </Reveal>

          <div className="mt-16">
            {/* connecting hairline */}
            <div className="relative">
              <div className="absolute left-0 right-0 top-[11px] hidden h-px bg-border lg:block" />
              <ol className="grid gap-10 lg:grid-cols-5 lg:gap-6">
                {PIPELINE.map((step, i) => (
                  <Reveal key={step.k} delay={i * 0.08}>
                    <li className="relative">
                      <div className="flex items-center gap-3 lg:block">
                        <span className="relative z-10 inline-flex h-[22px] w-[22px] items-center justify-center rounded-full border border-border bg-background">
                          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                        </span>
                        <span className="font-mono text-xs text-muted-foreground/60 lg:mt-4 lg:block">
                          0{i + 1}
                        </span>
                      </div>
                      <h3 className="mt-3 font-display text-lg font-semibold tracking-tight lg:mt-3">
                        {step.k}
                      </h3>
                      <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                        {step.d}
                      </p>
                    </li>
                  </Reveal>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </section>

      {/* ── Closing CTA (the lime crescendo) ───────────────────────────── */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-6 py-24 lg:px-10 lg:py-32">
          <Reveal>
            <div className="grain relative overflow-hidden rounded-2xl bg-accent px-8 py-16 text-accent-foreground lg:px-16 lg:py-24">
              <span className="eyebrow text-accent-foreground/70">Ready when you are</span>
              <h2 className="mt-6 max-w-3xl text-balance font-display text-[clamp(2.25rem,5.5vw,4.5rem)] font-semibold leading-[0.98] tracking-[-0.035em] text-accent-foreground">
                Deploy security that thinks.
              </h2>
              <p className="mt-6 max-w-lg text-base text-accent-foreground/80 lg:text-lg">
                Spin up the Echelon console, connect a pipeline, and watch every
                model decision get verified, scored, and recorded.
              </p>
              <div className="mt-10 flex flex-col gap-3 sm:flex-row">
                <button
                  onClick={onNavigateSignup}
                  className="group inline-flex items-center justify-center gap-2 rounded-md bg-foreground px-6 py-3 text-sm font-medium text-background transition-transform hover:-translate-y-0.5"
                >
                  Create your account
                  <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </button>
                <button
                  onClick={onNavigateLogin}
                  className="inline-flex items-center justify-center rounded-md border border-accent-foreground/25 px-6 py-3 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent-foreground/10"
                >
                  Sign in
                </button>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer className="bg-background">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-12 lg:flex-row lg:items-center lg:justify-between lg:px-10">
          <Wordmark size="sm" />
          <p className="eyebrow text-muted-foreground/60">
            © {new Date().getFullYear()} Echelon · Security for machine intelligence
          </p>
        </div>
      </footer>
    </div>
  );
}
