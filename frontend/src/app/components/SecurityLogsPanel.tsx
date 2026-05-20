import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Download, RefreshCw, Search, Shield } from 'lucide-react';
import {
  apiExportSecurityEvents,
  apiGetSecurityEvents,
  SecurityEvent,
  SecurityEventFilters,
} from '../api';
import { SecurityEventCard } from './logs/SecurityEventCard';

const CATEGORY_OPTIONS = [
  { value: '', label: 'All categories' },
  { value: 'inference', label: 'Inference' },
  { value: 'drift', label: 'Drift' },
  { value: 'training', label: 'Training' },
  { value: 'adversarial', label: 'Adversarial' },
  { value: 'integrity', label: 'Integrity' },
  { value: 'validation', label: 'Validation' },
  { value: 'system', label: 'System' },
];

const SEVERITY_OPTIONS = ['', 'INFO', 'WARNING', 'HIGH', 'CRITICAL'];

export function SecurityLogsPanel() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [filters, setFilters] = useState<SecurityEventFilters>({
    search: '',
    severity: '',
    category: '',
    model: '',
    date_from: '',
    date_to: '',
  });
  const latestEventId = useRef<string | null>(null);
  const eventIds = useRef<Set<string>>(new Set());

  const activeFilters = useMemo(
    () => ({
      search: filters.search || undefined,
      severity: filters.severity || undefined,
      category: filters.category || undefined,
      model: filters.model || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
    }),
    [filters],
  );

  const mergeEvents = useCallback((incoming: SecurityEvent[], replace = false) => {
    setEvents((prev) => {
      const ids = replace ? new Set<string>() : new Set(eventIds.current);
      const merged: SecurityEvent[] = replace ? [] : [...prev];
      for (const event of incoming) {
        if (ids.has(event.id)) continue;
        ids.add(event.id);
        merged.push(event);
      }
      eventIds.current = ids;
      merged.sort((a, b) => {
        if (a.timestamp === b.timestamp) return a.id < b.id ? 1 : -1;
        return a.timestamp < b.timestamp ? 1 : -1;
      });
      if (merged.length > 0) {
        latestEventId.current = merged[0].id;
      }
      return merged;
    });
  }, []);

  const fetchEvents = useCallback(
    async (targetPage = 1, append = false, showSpinner = true) => {
      if (showSpinner) {
        if (append) setLoadingMore(true);
        else setLoading(true);
      }
      setError('');
      try {
        const response = await apiGetSecurityEvents({
          ...activeFilters,
          page: targetPage,
          page_size: 50,
        });
        if (!response.ok) throw new Error(response.message || 'Failed to load security logs.');
        mergeEvents(response.events || [], !append && targetPage === 1);
        setHasMore(Boolean(response.pagination?.has_more));
        setPage(targetPage);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load security logs.');
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [activeFilters, mergeEvents],
  );

  const pollNewEvents = useCallback(async () => {
    if (!latestEventId.current || page !== 1) return;
    try {
      const response = await apiGetSecurityEvents({
        ...activeFilters,
        page: 1,
        page_size: 50,
        since_id: latestEventId.current,
      });
      if (response.ok && response.events?.length) {
        mergeEvents(response.events, false);
      }
    } catch {
      // Silent polling failure
    }
  }, [activeFilters, mergeEvents, page]);

  useEffect(() => {
    fetchEvents(1, false, true);
  }, [activeFilters]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const interval = setInterval(pollNewEvents, 12000);
    return () => clearInterval(interval);
  }, [pollNewEvents]);

  const handleExport = async (format: 'json' | 'csv') => {
    await apiExportSecurityEvents(format, activeFilters);
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-accent" />
            <h2 className="text-foreground">Security Event Console</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => fetchEvents(1, false, true)}
              className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:border-accent/40 hover:text-accent"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            <button
              type="button"
              onClick={() => handleExport('json')}
              className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:border-accent/40 hover:text-accent"
            >
              <Download className="h-4 w-4" />
              JSON
            </button>
            <button
              type="button"
              onClick={() => handleExport('csv')}
              className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:border-accent/40 hover:text-accent"
            >
              <Download className="h-4 w-4" />
              CSV
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              placeholder="Search events…"
              className="w-full rounded border border-border bg-background py-2 pl-9 pr-3 text-sm text-foreground"
            />
          </label>
          <select
            value={filters.severity}
            onChange={(e) => setFilters((prev) => ({ ...prev, severity: e.target.value }))}
            className="rounded border border-border bg-background px-3 py-2 text-sm text-foreground"
          >
            {SEVERITY_OPTIONS.map((option) => (
              <option key={option || 'all'} value={option}>
                {option || 'All severities'}
              </option>
            ))}
          </select>
          <select
            value={filters.category}
            onChange={(e) => setFilters((prev) => ({ ...prev, category: e.target.value }))}
            className="rounded border border-border bg-background px-3 py-2 text-sm text-foreground"
          >
            {CATEGORY_OPTIONS.map((option) => (
              <option key={option.value || 'all'} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            value={filters.model}
            onChange={(e) => setFilters((prev) => ({ ...prev, model: e.target.value }))}
            placeholder="Filter by model…"
            className="rounded border border-border bg-background px-3 py-2 text-sm text-foreground"
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => setFilters((prev) => ({ ...prev, date_from: e.target.value }))}
              className="rounded border border-border bg-background px-2 py-2 text-sm text-foreground"
            />
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => setFilters((prev) => ({ ...prev, date_to: e.target.value }))}
              className="rounded border border-border bg-background px-2 py-2 text-sm text-foreground"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border bg-card">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            <RefreshCw className="mr-2 h-5 w-5 animate-spin text-accent" />
            Loading security events…
          </div>
        ) : events.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-foreground">No security events match your filters.</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Events appear here as the platform runs inference, training, and monitoring.
            </p>
          </div>
        ) : (
          <div className="max-h-[calc(100vh-280px)] overflow-y-auto">
            {events.map((event) => (
              <SecurityEventCard
                key={event.id}
                event={event}
                expanded={expandedId === event.id}
                onToggle={() => setExpandedId((current) => (current === event.id ? null : event.id))}
              />
            ))}
          </div>
        )}

        {hasMore && !loading && (
          <div className="border-t border-border p-4 text-center">
            <button
              type="button"
              disabled={loadingMore}
              onClick={() => fetchEvents(page + 1, true, false)}
              className="rounded border border-border px-4 py-2 text-sm text-muted-foreground transition-colors hover:border-accent/40 hover:text-accent disabled:opacity-50"
            >
              {loadingMore ? 'Loading…' : 'Load more events'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
