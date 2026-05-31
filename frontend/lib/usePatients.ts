"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "./api";
import { PacketLoadError } from "./usePacket";

/**
 * Live patient list from ``GET /patients``. Reuses the ``PacketLoadError``
 * shape so the retry-skip-on-4xx predicate (`shouldRetry` in providers.tsx)
 * applies here too — a fresh checkout missing NEXT_PUBLIC_API_TOKEN gives the
 * same diagnostic surface across every backend-bound query.
 */
export function usePatients() {
  return useQuery({
    queryKey: ["patients"],
    queryFn: async () => {
      const start = performance.now();
      const result = await apiClient.GET("/patients", {});
      const elapsedMs = Math.round(performance.now() - start);
      // openapi-fetch narrows `error` to `never` when the spec declares only
      // a 2xx response (it does for /patients), so we read `response` via a
      // broader Response type to stay honest about runtime failures.
      const { data, error } = result;
      const response = (result as { response?: Response }).response;
      if (error !== undefined || !data) {
        throw new PacketLoadError({
          status: response?.status,
          body: (error as unknown) ?? null,
          url: response?.url ?? "",
          elapsedMs,
        });
      }
      return data;
    },
  });
}
