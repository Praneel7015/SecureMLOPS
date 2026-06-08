import { cn } from '../ui/utils';

interface EchelonMarkProps {
  className?: string;
  /** Tint the leading bar with the lime accent (the single surgical accent). */
  accent?: boolean;
}

/**
 * Echelon mark — three ascending stepped bars ("echelon formation").
 * Geometric, Swiss, and meaningful: rank/level/ascending defense posture.
 */
export function EchelonMark({ className, accent = true }: EchelonMarkProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={cn('h-6 w-6', className)}
    >
      <rect x="2" y="14" width="5.2" height="8" rx="1.2" className="fill-current" opacity="0.55" />
      <rect x="9.4" y="9" width="5.2" height="13" rx="1.2" className="fill-current" opacity="0.8" />
      <rect
        x="16.8"
        y="3.5"
        width="5.2"
        height="18.5"
        rx="1.2"
        className={accent ? 'fill-accent' : 'fill-current'}
      />
    </svg>
  );
}

interface WordmarkProps {
  className?: string;
  /** Size of the lockup. */
  size?: 'sm' | 'md' | 'lg';
  /** Hide the text and show only the mark. */
  markOnly?: boolean;
  accent?: boolean;
}

const SIZES = {
  sm: { mark: 'h-5 w-5', text: 'text-base', gap: 'gap-2' },
  md: { mark: 'h-6 w-6', text: 'text-lg', gap: 'gap-2.5' },
  lg: { mark: 'h-8 w-8', text: 'text-2xl', gap: 'gap-3' },
} as const;

export function Wordmark({ className, size = 'md', markOnly = false, accent = true }: WordmarkProps) {
  const s = SIZES[size];
  return (
    <span className={cn('inline-flex items-center', s.gap, className)}>
      <EchelonMark className={s.mark} accent={accent} />
      {!markOnly && (
        <span
          className={cn(
            'font-display font-semibold tracking-tight text-foreground',
            s.text,
          )}
        >
          Echelon
        </span>
      )}
    </span>
  );
}
