"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { PacketLoadError, isNonRetryableStatus } from "../lib/usePacket";

/**
 * Default queries:
 * - Skip retries on 4xx (auth / not-found / validation): retrying turns a
 *   fast 401 into a ~7s spinner-of-doom before the error UI appears. See
 *   #90 — this was the dominant symptom on the deployed Cloud Run build.
 * - 5xx and network errors still get the default 3-retry budget.
 *
 * The check is scoped to ``PacketLoadError`` so other callers' retry behaviour
 * stays at the TanStack defaults. As more endpoints adopt diagnostic-bearing
 * error classes, this predicate can broaden.
 */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof PacketLoadError && isNonRetryableStatus(error.diag.status)) {
    return false;
  }
  return failureCount < 3;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: shouldRetry,
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
