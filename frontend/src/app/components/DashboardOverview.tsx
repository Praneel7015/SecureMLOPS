import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import {
  Activity,
  AlertTriangle,
  Database,
  FileCheck,
  PlayCircle,
  RefreshCw,
  Shield,
  TrendingUp,
  Zap,
} from 'lucide-react';
import {
  apiGetDashboardActivity,
  apiGetDashboardSecuritySummary,
  apiGetDashboardSummary,
  DashboardSummary,
  SecurityEvent,
} from '../api';
import { SeverityBadge } from './logs/SeverityBadge';

type DashboardOverviewProps = {
  username: string;
  refreshToken?: number;
};

const formatTimestamp = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const formatPercent = (value?: number | null) => {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
};

function Panel({
  title,
  action,
  children,
  className,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-col rounded-xl border border-border bg-card ${className ?? ''}`}>
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <h2 className="font-display text-base font-semibold tracking-tight text-foreground">
          {title}
        </h2>
        {action}
      </div>
      <div className="flex-1 p-5">{children}</div>
    </div>
  );
}

const StatusDot = ({ value }: { value?: string }) => {
  const v = (value || '').toLowerCase();
  const tone =
    v.includes('active') || v.includes('online') || v.includes('running') || v.includes('healthy')
      ? 'bg-success'
      : v.includes('idle') || v.includes('paused')
        ? 'bg-warning'
        : v.includes('error') || v.includes('down') || v.includes('unavailable')
          ? 'bg-destructive'
          : 'bg-muted-foreground/40';
  return <span className={`h-1.5 w-1.5 rounded-full ${tone}`} />;
};

export function DashboardOverview({ refreshToken = 0 }: DashboardOverviewProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [activity, setActivity] = useState<SecurityEvent[]>([]);
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const seenActivityIds = useRef<Set<string>>(new Set());

  const loadData = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    setError('');
    try {
      const [summaryRes, activityRes, securityRes] = await Promise.all([
        apiGetDashboardSummary(),
        apiGetDashboardActivity(25),
        apiGetDashboardSecuritySummary(8),
      ]);

      if (!summaryRes.ok || !activityRes.ok || !securityRes.ok) {
        throw new Error('Failed to load dashboard data.');
      }

      setSummary(summaryRes.summary || null);

      const nextActivity = activityRes.activity || [];
      const mergedActivity = [...nextActivity];
      for (const event of mergedActivity) {
        seenActivityIds.current.add(event.id);
      }
      setActivity(mergedActivity);

      setSecurityEvents(securityRes.events || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData(true);
  }, [loadData, refreshToken]);

  useEffect(() => {
    const interval = setInterval(() => loadData(false), 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-muted-foreground">
        <RefreshCw className="h-4 w-4 animate-spin text-accent" />
        <span className="eyebrow">Loading overview…</span>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-destructive">
        {error}
      </div>
    );
  }

  const metrics = summary?.metrics;
  const systemStatus = summary?.system_status;

  const metricCards = [
    { label: 'Total Inferences', value: metrics?.total_inferences ?? 0, icon: Zap },
    { label: 'High Risk Events', value: metrics?.high_risk_events ?? 0, icon: AlertTriangle },
    { label: 'Drift Alerts', value: metrics?.drift_alerts ?? 0, icon: TrendingUp },
    { label: 'Poisoning Alerts', value: metrics?.poisoning_alerts ?? 0, icon: Shield },
    { label: 'Dataset Scans', value: metrics?.poisoning_scan_activity ?? 0, icon: Shield },
    { label: 'Suspicious Datasets', value: metrics?.suspicious_dataset_uploads ?? 0, icon: AlertTriangle },
    { label: 'High-Risk Training', value: metrics?.high_risk_training_attempts ?? 0, icon: Activity },
    { label: 'Flagged Samples', value: metrics?.poisoned_sample_count ?? 0, icon: FileCheck },
    { label: 'Models Registered', value: metrics?.models_registered ?? 0, icon: FileCheck },
    { label: 'Active Training', value: metrics?.active_training_jobs ?? 0, icon: PlayCircle },
    { label: 'Last Train Acc.', value: formatPercent(metrics?.last_training_accuracy), icon: Activity },
    { label: 'Avg Drift Score', value: metrics?.average_drift_score ?? 0, icon: TrendingUp },
    {
      label: 'Detector',
      value: metrics?.poisoning_detector_available ? 'Online' : 'Unavailable',
      icon: Shield,
    },
    { label: 'Total Events', value: metrics?.total_events ?? 0, icon: Shield },
  ];

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="eyebrow text-accent">Console / Overview</span>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight text-foreground">
            Operational overview
          </h1>
        </div>
        <button
          type="button"
          onClick={() => loadData(false)}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Metric grid — razor hairline cells */}
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border lg:grid-cols-4 xl:grid-cols-7">
        {metricCards.map((card) => (
          <div key={card.label} className="bg-card p-5">
            <div className="flex items-center justify-between">
              <span className="eyebrow text-muted-foreground/60">{card.label}</span>
              <card.icon className="h-4 w-4 text-muted-foreground/40" strokeWidth={1.75} />
            </div>
            <div className="mt-3 font-mono text-3xl font-medium tracking-tight text-foreground">
              {card.value}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel
          title="Recent activity"
          className="xl:col-span-2"
          action={
            <button
              type="button"
              onClick={() => loadData(false)}
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </button>
          }
        >
          {activity.length === 0 ? (
            <p className="font-mono text-sm text-muted-foreground">No platform activity recorded yet.</p>
          ) : (
            <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
              {activity.map((event) => (
                <div
                  key={event.id}
                  className="rounded-lg border border-border bg-background/40 p-3 transition-colors hover:border-border-strong"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={event.severity} />
                    <span className="font-mono text-xs text-muted-foreground">
                      {formatTimestamp(event.timestamp)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-foreground">{event.title}</p>
                  <p className="mt-1 truncate font-mono text-xs text-muted-foreground">
                    {event.description}
                  </p>
                  {(event.metadata?.model_name || event.metadata?.job_id) && (
                    <p className="mt-1 font-mono text-xs text-accent">
                      {event.metadata?.model_name || event.metadata?.job_id}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="System status">
          <div className="space-y-3 text-sm">
            {[
              ['Monitoring', systemStatus?.monitoring_status, true],
              ['Drift Monitoring', systemStatus?.drift_monitoring_status, true],
              ['Poisoning Detector', systemStatus?.poisoning_detector_status || 'unknown', true],
              ['Security Engine', systemStatus?.security_engine_status, true],
              ['Last Inference', formatTimestamp(systemStatus?.last_inference_at), false],
              ['Last Drift Event', formatTimestamp(systemStatus?.last_drift_event_at), false],
              ['Last Poisoning Event', formatTimestamp(systemStatus?.last_poisoning_event_at), false],
            ].map(([label, value, dot]) => (
              <div
                key={label as string}
                className="flex items-center justify-between gap-3 border-b border-border/60 pb-2.5 last:border-0 last:pb-0"
              >
                <span className="text-muted-foreground">{label}</span>
                <span className="flex items-center gap-2 truncate font-mono text-xs text-foreground">
                  {dot ? <StatusDot value={value as string} /> : null}
                  {(value as string) || '—'}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel title="Recent training">
          {(summary?.recent_training || []).length === 0 ? (
            <p className="font-mono text-sm text-muted-foreground">No training jobs yet.</p>
          ) : (
            <div className="space-y-2">
              {summary?.recent_training.map((job) => (
                <div key={job.job_id} className="rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-accent">{job.model_type || 'unknown'}</span>
                    <span className="font-mono text-[0.7rem] uppercase tracking-wider text-muted-foreground">
                      {job.status}
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm text-foreground">
                    Val accuracy: {formatPercent(job.validation_accuracy)}
                  </p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {formatTimestamp(job.updated_at || job.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Recent security events">
          {securityEvents.length === 0 ? (
            <p className="font-mono text-sm text-muted-foreground">No security events recorded.</p>
          ) : (
            <div className="space-y-2">
              {securityEvents.map((event) => (
                <details key={event.id} className="group rounded-lg border border-border p-3">
                  <summary className="cursor-pointer list-none">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={event.severity} />
                      <span className="truncate text-sm text-foreground">{event.title}</span>
                    </div>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {formatTimestamp(event.timestamp)}
                    </p>
                  </summary>
                  <p className="mt-2 font-mono text-xs text-muted-foreground">{event.description}</p>
                </details>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Model registry">
          {(summary?.recent_models || []).length === 0 ? (
            <p className="font-mono text-sm text-muted-foreground">No registered models yet.</p>
          ) : (
            <div className="space-y-2">
              {summary?.recent_models.map((model) => (
                <div key={model.model_id} className="rounded-lg border border-border p-3">
                  <div className="flex items-center gap-2">
                    <Database className="h-3.5 w-3.5 text-muted-foreground/50" />
                    <p className="text-sm text-foreground">{model.model_label || model.model_type}</p>
                  </div>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    {model.num_classes} classes · {model.inference_ready ? 'inference ready' : 'pending'}
                  </p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {formatTimestamp(model.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
