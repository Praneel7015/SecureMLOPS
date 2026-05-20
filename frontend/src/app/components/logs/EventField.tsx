export type EventFieldVariant = 'default' | 'badge' | 'metric';

export type EventFieldProps = {
  label: string;
  value?: string | number | boolean | null;
  variant?: EventFieldVariant;
  highlight?: boolean;
};

const formatValue = (value?: string | number | boolean | null) => {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
};

export function EventField({ label, value, variant = 'default', highlight = false }: EventFieldProps) {
  const display = formatValue(value);

  if (variant === 'badge') {
    return (
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="inline-flex w-fit rounded-full border border-border/80 bg-background/60 px-2.5 py-0.5 text-xs text-foreground">
          {display}
        </span>
      </div>
    );
  }

  if (variant === 'metric') {
    return (
      <div className="rounded-md border border-border/70 bg-background/50 p-3">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={`mt-1 text-lg tabular-nums ${highlight ? 'text-accent' : 'text-foreground'}`}>
          {display}
        </p>
      </div>
    );
  }

  return (
    <div className="min-w-0">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-0.5 truncate text-sm ${highlight ? 'text-accent' : 'text-foreground'}`} title={display}>
        {display}
      </p>
    </div>
  );
}
