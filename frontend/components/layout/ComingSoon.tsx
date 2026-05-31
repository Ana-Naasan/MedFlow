import type { LucideIcon } from "lucide-react";

interface ComingSoonProps {
  icon: LucideIcon;
  title: string;
  description: string;
  features?: string[];
}

/**
 * Placeholder for routes that exist in the medflow IA but aren't yet bound to
 * an umraa backend endpoint. Same visual shape as medflow's ComingSoon so
 * navigating between the implemented and unimplemented tabs feels coherent.
 */
export function ComingSoon({
  icon: Icon,
  title,
  description,
  features = [],
}: ComingSoonProps) {
  return (
    <div
      className="flex min-h-[400px] items-center justify-center px-6"
      data-testid="coming-soon"
    >
      <div className="w-full max-w-xl text-center">
        <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-bg-subtle">
          <Icon className="size-8 text-accent" strokeWidth={1.5} aria-hidden />
        </div>

        <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-accent/10 px-3 py-1">
          <span className="size-1.5 animate-pulse rounded-full bg-accent" />
          <span className="text-xs font-medium uppercase tracking-wider text-accent">
            Coming Soon
          </span>
        </div>

        <h2 className="mb-3 mf-display text-3xl font-semibold text-foreground">
          {title}
        </h2>
        <p className="text-sm text-mf-ink-soft">{description}</p>

        {features.length > 0 && (
          <ul className="mt-6 inline-block text-left text-sm text-mf-ink-soft">
            {features.map((f) => (
              <li key={f} className="mb-1">
                · {f}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
