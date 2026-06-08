import { useCallback, useEffect, useRef, useState } from 'react';
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

export function DashboardOverview({ username, refreshToken = 0 }: DashboardOverviewProps) {
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
      <div className="flex items-center justify-center py-20 text-muted-foreground">
        <RefreshCw className="mr-2 h-5 w-5 animate-spin text-accent" />
        Loading operational dashboard…
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

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Total Inferences', value: metrics?.total_inferences ?? 0, icon: Zap },
          { label: 'High Risk Events', value: metrics?.high_risk_events ?? 0, icon: AlertTriangle },
          { label: 'Drift Alerts', value: metrics?.drift_alerts ?? 0, icon: TrendingUp },
          { label: 'Dataset Security Scans', value: metrics?.poisoning_scan_activity ?? 0, icon: Shield },
          { label: 'Poisoning Alerts', value: metrics?.poisoning_alerts ?? 0, icon: Shield },
          { label: 'Suspicious Datasets', value: metrics?.suspicious_dataset_uploads ?? 0, icon: AlertTriangle },
          { label: 'High-Risk Training', value: metrics?.high_risk_training_attempts ?? 0, icon: Activity },
          { label: 'Flagged Samples', value: metrics?.poisoned_sample_count ?? 0, icon: FileCheck },
          { label: 'Models Registered', value: metrics?.models_registered ?? 0, icon: FileCheck },
          { label: 'Active Training Jobs', value: metrics?.active_training_jobs ?? 0, icon: PlayCircle },
          {
            label: 'Last Training Accuracy',
            value: formatPercent(metrics?.last_training_accuracy),
            icon: Activity,
          },
          { label: 'Average Drift Score', value: metrics?.average_drift_score ?? 0, icon: TrendingUp },
          {
            label: 'Detector Availability',
            value: metrics?.poisoning_detector_available ? 'Online' : 'Unavailable',
            icon: Shield,
          },
          { label: 'Total Events', value: metrics?.total_events ?? 0, icon: Shield },
        ].map((card) => (
          <div key={card.label} className="rounded-lg border border-border bg-card p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{card.label}</span>
              <card.icon className="h-5 w-5 text-accent" />
            </div>
            <div className="text-2xl text-foreground">{card.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-6 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-foreground">Recent Activity</h2>
            <button
              type="button"
              onClick={() => loadData(false)}
              className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-accent"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
          {activity.length === 0 ? (
            <p className="font-mono text-sm text-muted-foreground">No platform activity recorded yet.</p>
          ) : (
            <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
              {activity.map((event) => (
                <div
                  key={event.id}
                  className="rounded-md border border-border/70 bg-background/40 p-3"
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
        </div>

        <div className="rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-foreground">Quick System Status</h2>
          <div className="space-y-3 font-mono text-sm">
            {[
              ['Monitoring', systemStatus?.monitoring_status],
              ['Drift Monitoring', systemStatus?.drift_monitoring_status],
              ['Poisoning Detector', systemStatus?.poisoning_detector_status || 'unknown'],
              ['Security Engine', systemStatus?.security_engine_status],
              ['Last Inference', formatTimestamp(systemStatus?.last_inference_at)],
              ['Last Drift Event', formatTimestamp(systemStatus?.last_drift_event_at)],
              ['Last Poisoning Event', formatTimestamp(systemStatus?.last_poisoning_event_at)],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between gap-3 border-b border-border/50 pb-2">
                <span className="text-muted-foreground">{label}</span>
                <span className="truncate text-foreground">{value || '—'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-foreground">Recent Training</h2>
          {(summary?.recent_training || []).length === 0 ? (
            <p className="font-mono text-sm text-muted-foreground">No training jobs yet.</p>
          ) : (
            <div className="space-y-3">
              {summary?.recent_training.map((job) => (
                <div key={job.job_id} className="rounded-md border border-border/70 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-accent">{job.model_type || 'unknown'}</span>
                    <span className="font-mono text-xs uppercase text-muted-foreground">{job.status}</span>
                  </div>
                  <p className="mt-1 text-sm text-foreground">
                    Val accuracy: {formatPercent(job.validation_accuracy)}
                  </p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {formatTimestamp(job.updated_at || job.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-foreground">Recent Security Events</h2>
          {securityEvents.length === 0 ? (
            <p className="font-mono text-sm text-muted-foreground">No security events recorded.</p>
          ) : (
            <div className="space-y-3">
              {securityEvents.map((event) => (
                <details key={event.id} className="rounded-md border border-border/70 p-3">
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
        </div>

        <div className="rounded-lg border border-border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <Database className="h-5 w-5 text-accent" />
            <h2 className="text-foreground">Model Registry Snapshot</h2>
          </div>
          {(summary?.recent_models || []).length === 0 ? (
            <p className="font-mono text-sm text-muted-foreground">No registered models yet.</p>
          ) : (
            <div className="space-y-3">
              {summary?.recent_models.map((model) => (
                <div key={model.model_id} className="rounded-md border border-border/70 p-3">
                  <p className="text-sm text-foreground">{model.model_label || model.model_type}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {model.num_classes} classes · {model.inference_ready ? 'inference ready' : 'pending'}
                  </p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {formatTimestamp(model.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <p className="font-mono text-xs text-muted-foreground">Signed in as {username}</p>
    </div>
  );
}
