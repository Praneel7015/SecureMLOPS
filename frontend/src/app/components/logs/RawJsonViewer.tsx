import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

type RawJsonViewerProps = {
  metadata: Record<string, unknown>;
};

export function RawJsonViewer({ metadata }: RawJsonViewerProps) {
  const [open, setOpen] = useState(false);
  const hasData = Object.keys(metadata).length > 0;

  if (!hasData) return null;

  return (
    <div className="mt-4 border-t border-border/40 pt-3">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        View Raw JSON
      </button>
      {open && (
        <pre className="mt-2 max-h-40 overflow-auto rounded border border-border/50 bg-background/30 p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">
          {JSON.stringify(metadata, null, 2)}
        </pre>
      )}
    </div>
  );
}
