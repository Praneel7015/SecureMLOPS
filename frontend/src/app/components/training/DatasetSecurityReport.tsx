import { RefreshCw, Shield } from 'lucide-react';
import { DatasetSecurityReport } from '../../api';

type DatasetSecurityReportCardProps = {
  report?: DatasetSecurityReport | null;
  title?: string;
  isLoading?: boolean;
};

const severityClass = (severity?: string) => {
  if (severity === 'HIGH') return 'bg-destructive/20 text-destructive';
  if (severity === 'MEDIUM') return 'bg-warning/20 text-warning';
  if (severity === 'UNAVAILABLE') return 'bg-muted/40 text-muted-foreground';
  return 'bg-success/20 text-success';
};

const formatPercent = (value?: number | null) => {
  if (value === null || value === undefined) return 'N/A';
  return `${(value * 100).toFixed(0)}%`;
};

export function DatasetSecurityReportCard({
  report,
  title = 'Dataset Security Scan',
  isLoading = false,
}: DatasetSecurityReportCardProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="mb-3 flex items-center gap-2">
          <RefreshCw className="h-5 w-5 animate-spin text-accent" />
          <h3 className="text-foreground">{title}</h3>
        </div>
        <p className="font-mono text-sm text-muted-foreground">
          Validating dataset and running poisoning security scan...
        </p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="mb-3 flex items-center gap-2">
          <Shield className="h-5 w-5 text-accent" />
          <h3 className="text-foreground">{title}</h3>
        </div>
        <p className="font-mono text-sm text-muted-foreground">
          Upload a dataset to run the poisoning security scan.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-accent" />
          <h3 className="text-foreground">{title}</h3>
        </div>
        <span className={`rounded px-2 py-1 text-xs font-mono ${severityClass(report.dataset_risk_level)}`}>
          {report.dataset_risk_level || 'UNAVAILABLE'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 font-mono text-sm text-muted-foreground">
        <div>Images Scanned: <span className="text-foreground">{report.images_scanned ?? 0}</span></div>
        <div>Suspicious Samples: <span className="text-foreground">{report.suspicious_count ?? 0}</span></div>
        <div>Average Risk Score: <span className="text-foreground">{report.average_poison_probability ?? 'N/A'}</span></div>
        <div>Highest Poison Probability: <span className="text-foreground">{formatPercent(report.highest_poison_probability)}</span></div>
        <div>Detector: <span className="text-foreground">{report.detector_type || 'MLP'}</span></div>
        <div>Training Decision: <span className="text-foreground uppercase">{report.training_decision || 'allow'}</span></div>
      </div>

      <div className="rounded-md border border-border/70 bg-background/40 p-3">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">Recommendation</p>
        <p className="mt-1 text-sm text-foreground">{report.recommendation || 'No recommendation available.'}</p>
      </div>
    </div>
  );
}
