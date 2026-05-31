"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "./api";

/**
 * Diagnostic surface for a failed packet fetch.
 *
 * Built explicitly so the error UI can show the operator why the request
 * failed (status, body, URL, elapsed) without having to dig through devtools
 * or GCP logs — see #90.
 */
export interface PacketLoadDiagnostic {
  /** HTTP status code; ``undefined`` when no response was received (network
   * error, CORS preflight failure, backend unreachable). */
  status: number | undefined;
  /** Parsed error body from the response (e.g. ``{detail: "Missing bearer token"}``)
   * or ``null`` if no body was available. */
  body: unknown;
  /** Final request URL (post-redirect when applicable). Useful when the
   * baseUrl is misconfigured — the wrong host shows up here. */
  url: string;
  /** Wall-clock duration of the fetch in milliseconds. */
  elapsedMs: number;
}

/**
 * Error class thrown by ``usePacket``'s queryFn on a non-2xx or network
 * failure. The diagnostic struct is exposed so the retry policy + the
 * error UI can both read it without parsing the message string.
 */
export class PacketLoadError extends Error {
  readonly diag: PacketLoadDiagnostic;

  constructor(diag: PacketLoadDiagnostic) {
    super(
      diag.status !== undefined
        ? `Packet fetch failed: HTTP ${diag.status}`
        : "Packet fetch failed: no response (network or CORS)",
    );
    this.name = "PacketLoadError";
    this.diag = diag;
  }
}

/**
 * Returns ``true`` for HTTP statuses where retrying is pointless — auth,
 * not-found, validation. 5xx and missing-status (network) failures still
 * fall through to the QueryClient's default retry budget.
 */
export function isNonRetryableStatus(status: number | undefined): boolean {
  return status !== undefined && status >= 400 && status < 500;
}

/**
 * Fetch ``/patients/{patient_id}/packet`` with diagnostic-bearing errors.
 *
 * Mirrors what ``$api.useQuery`` would do but throws ``PacketLoadError``
 * instead of swallowing the response status, so:
 *
 * - the QueryClient's retry policy can skip 4xx without hammering
 *   unrecoverable failures (the slow-failure UX in #90), and
 * - the page can render the actual cause (401? 404? network?) instead of
 *   the previous opaque "Failed to load packet."
 */
export function usePacket(patientId: string) {
  return useQuery({
    queryKey: ["packet", patientId],
    queryFn: async () => {
      const start = performance.now();
      const { data, error, response } = await apiClient.GET(
        "/patients/{patient_id}/packet",
        { params: { path: { patient_id: patientId } } },
      );
      const elapsedMs = Math.round(performance.now() - start);

      if (error !== undefined || !data) {
        throw new PacketLoadError({
          status: response?.status,
          body: error ?? null,
          url: response?.url ?? "",
          elapsedMs,
        });
      }
      return data;
    },
  });
}
