type SeverityBadgeProps = {
  severity: string;
  className?: string;
};

const SEVERITY_STYLES: Record<string, string> = {
  INFO: 'bg-accent/15 text-accent border-accent/30',
  WARNING: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  HIGH: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  CRITICAL: 'bg-destructive/15 text-destructive border-destructive/30',
};

export function SeverityBadge({ severity, className = '' }: SeverityBadgeProps) {
  const normalized = (severity || 'INFO').toUpperCase();
  const style = SEVERITY_STYLES[normalized] || SEVERITY_STYLES.INFO;

  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-xs uppercase tracking-wide ${style} ${className}`}
    >
      {normalized}
    </span>
  );
}

export const SEVERITY_ACCENT: Record<string, string> = {
  INFO: 'border-l-accent',
  WARNING: 'border-l-yellow-500',
  HIGH: 'border-l-orange-500',
  CRITICAL: 'border-l-destructive',
};
