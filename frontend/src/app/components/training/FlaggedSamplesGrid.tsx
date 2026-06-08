import { useState } from 'react';
import { FlaggedSample } from '../../api';

type FlaggedSamplesGridProps = {
  samples?: FlaggedSample[];
};

const severityClass = (severity?: string) => {
  if (severity === 'HIGH') return 'bg-destructive/20 text-destructive';
  if (severity === 'MEDIUM') return 'bg-warning/20 text-warning';
  return 'bg-muted/40 text-muted-foreground';
};

export function FlaggedSamplesGrid({ samples = [] }: FlaggedSamplesGridProps) {
  const [expandedPath, setExpandedPath] = useState<string | null>(null);

  if (!samples.length) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="mb-2 text-foreground">Flagged Samples</h3>
        <p className="font-mono text-sm text-muted-foreground">No suspicious samples flagged in this dataset.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-foreground">Flagged Samples</h3>
        <span className="font-mono text-xs text-muted-foreground">{samples.length} shown</span>
      </div>

      <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
        {samples.map((sample) => {
          const expanded = expandedPath === sample.relative_path;
          return (
            <div key={sample.relative_path} className="rounded-lg border border-border/70 bg-background/30 p-3">
              <button
                type="button"
                className="flex w-full items-start justify-between gap-3 text-left"
                onClick={() => setExpandedPath(expanded ? null : sample.relative_path)}
              >
                <div className="min-w-0">
                  <div className="truncate font-mono text-sm text-foreground">{sample.filename}</div>
                  <div className="font-mono text-xs text-muted-foreground">{sample.class_name}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded px-2 py-1 text-xs font-mono ${severityClass(sample.severity)}`}>
                    {sample.severity}
                  </span>
                  <span className="font-mono text-sm text-accent">
                    {(sample.poison_probability * 100).toFixed(0)}%
                  </span>
                </div>
              </button>

              {expanded && sample.preview_url && (
                <div className="mt-3 overflow-hidden rounded-md border border-border/70 bg-muted/20 p-2">
                  <img
                    src={sample.preview_url}
                    alt={sample.filename}
                    className="mx-auto max-h-48 rounded object-contain"
                  />
                  <p className="mt-2 truncate font-mono text-xs text-muted-foreground">{sample.relative_path}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
