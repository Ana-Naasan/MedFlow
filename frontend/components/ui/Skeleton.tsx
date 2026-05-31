import type { HTMLAttributes } from "react";

import { cn } from "../../lib/utils";

/**
 * Skeleton placeholder for loading states. Pulses gently — the citation modal
 * uses its own shimmer for backwards compat; this one is for the dashboard /
 * directory pages.
 */
export function Skeleton({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-mf-paper-2",
        className,
      )}
      role="status"
      aria-label="Loading"
      {...props}
    />
  );
}
