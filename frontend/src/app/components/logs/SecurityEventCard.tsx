import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileCheck,
  LucideIcon,
  Shield,
  Zap,
} from 'lucide-react';
import { SecurityEvent } from '../../api';
import { EventMetadataGrid } from './EventMetadataGrid';
import { RawJsonViewer } from './RawJsonViewer';
import { SeverityBadge, SEVERITY_ACCENT } from './SeverityBadge';
import {
  formatEventTimestamp,
  getEventCategory,
  getEventMetadataFields,
  getEventStatusSummary,
} from './eventMetadata';

type SecurityEventCardProps = {
  event: SecurityEvent;
  expanded: boolean;
  onToggle: () => void;
};

const eventIcon = (eventType: string): LucideIcon => {
  if (eventType.startsWith('inference')) return Zap;
  if (eventType.startsWith('adversarial') || eventType.startsWith('integrity') || eventType.startsWith('poisoning')) return Shield;
  if (eventType.startsWith('drift')) return AlertTriangle;
  return FileCheck;
};

export function SecurityEventCard({ event, expanded, onToggle }: SecurityEventCardProps) {
  const Icon = eventIcon(event.event_type);
  const severityKey = (event.severity || 'INFO').toUpperCase();
  const accent = SEVERITY_ACCENT[severityKey] || SEVERITY_ACCENT.INFO;
  const fields = getEventMetadataFields(event);
  const statusSummary = getEventStatusSummary(event);
  const category = getEventCategory(event.event_type);

  return (
    <article
      className={`border-b border-border/60 border-l-[3px] bg-card/40 transition-colors hover:bg-background/30 ${accent} ${
        expanded ? 'bg-background/20' : ''
      }`}
    >
      <button
        type="button"
        className="flex w-full items-start gap-3 px-4 py-3.5 text-left"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border/70 bg-background/50">
          <Icon className="h-4 w-4 text-accent" />
        </div>

        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={event.severity} />
            <span className="rounded-full border border-border/70 bg-background/40 px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
              {category}
            </span>
            <span className="font-mono text-[11px] text-muted-foreground/80">{event.event_type}</span>
          </div>

          <div>
            <h3 className="text-sm font-medium text-foreground">{event.title}</h3>
            <p className="mt-0.5 font-mono text-xs text-muted-foreground">
              {formatEventTimestamp(event.timestamp)}
            </p>
          </div>

          <p className="line-clamp-2 text-sm text-muted-foreground">{statusSummary}</p>
        </div>

        <div className="flex shrink-0 items-center pt-1">
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="space-y-3 border-t border-border/40 px-4 pb-4 pt-3">
          <div className="rounded-md border border-border/60 bg-background/30 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Event Details
              </p>
              <span className="text-xs text-muted-foreground">Source: {event.source}</span>
            </div>
            <EventMetadataGrid fields={fields} />
            <RawJsonViewer metadata={event.metadata || {}} />
          </div>

          {event.description && event.description !== statusSummary && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground/80">Description: </span>
              {event.description}
            </p>
          )}
        </div>
      )}
    </article>
  );
}
