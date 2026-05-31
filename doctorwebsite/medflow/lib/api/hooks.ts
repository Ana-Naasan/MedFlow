"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { apiClient } from "./client";
import type {
  AuditEvent,
  DecisionPacket,
  EvidenceSnippet,
  IntakeRequest,
  IntakeResponse,
} from "./types";

/** Query key for a patient's decision packet. Mutations invalidate this. */
export function packetQueryKey(patientId: string) {
  return ["packet", patientId] as const;
}

/**
 * Read an HTTP status off an openapi-fetch `response` without tripping the
 * type narrowing that collapses `response` to `never` on endpoints whose
 * schema declares no error variant. Returns "no response" for network errors.
 */
function statusOf(response: unknown): string {
  const status = (response as { status?: unknown } | undefined)?.status;
  return typeof status === "number" ? String(status) : "no response";
}

/* -------------------------------------------------------------------------- */
/* Packet diagnostics (ported from frontend/lib/usePacket.ts)                  */
/* -------------------------------------------------------------------------- */

/**
 * Diagnostic surface for a failed packet fetch.
 *
 * Built explicitly so the error UI can show the operator why the request
 * failed (status, body, URL, elapsed) without having to dig through devtools
 * or backend logs.
 */
export interface PacketLoadDiagnostic {
  /** HTTP status code; `undefined` when no response was received (network
   * error, CORS preflight failure, backend unreachable). */
  status: number | undefined;
  /** Parsed error body from the response (e.g. `{detail: "Missing bearer token"}`)
   * or `null` if no body was available. */
  body: unknown;
  /** Final request URL (post-redirect when applicable). Useful when the
   * baseUrl is misconfigured — the wrong host shows up here. */
  url: string;
  /** Wall-clock duration of the fetch in milliseconds. */
  elapsedMs: number;
}

/**
 * Error class thrown by `usePacket`'s queryFn on a non-2xx or network
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
 * Returns `true` for HTTP statuses where retrying is pointless — auth,
 * not-found, validation. 5xx and missing-status (network) failures still
 * fall through to the QueryClient's default retry budget.
 */
export function isNonRetryableStatus(status: number | undefined): boolean {
  return status !== undefined && status >= 400 && status < 500;
}

/* -------------------------------------------------------------------------- */
/* Queries                                                                     */
/* -------------------------------------------------------------------------- */

/**
 * List patient IDs from `GET /patients`. The endpoint is untyped, so this
 * normalizes the three observed shapes — `{patients: string[]}`, a bare
 * `string[]`, or an array of objects with an `id`/`patient_id` field — down to
 * a clean `string[]`.
 */
export function usePatients() {
  return useQuery<string[]>({
    queryKey: ["patients"],
    queryFn: async () => {
      const { data, error, response } = await apiClient.GET("/patients");
      if (error !== undefined || !data) {
        throw new Error(
          `Failed to load patients: HTTP ${statusOf(response)}`,
        );
      }
      return normalizePatientIds(data);
    },
  });
}

/**
 * Coerce the untyped `/patients` body into a `string[]` of patient IDs.
 * Handles `{patients: [...]}`, a bare array, and arrays of objects carrying an
 * `id` / `patient_id` / `patientId` field.
 */
function normalizePatientIds(raw: unknown): string[] {
  const list = Array.isArray(raw)
    ? raw
    : raw && typeof raw === "object" && Array.isArray((raw as { patients?: unknown }).patients)
      ? ((raw as { patients: unknown[] }).patients)
      : [];

  return list
    .map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object") {
        const obj = item as Record<string, unknown>;
        const id = obj.id ?? obj.patient_id ?? obj.patientId;
        return typeof id === "string" ? id : null;
      }
      return null;
    })
    .filter((id): id is string => typeof id === "string" && id.length > 0);
}

/**
 * Fetch `GET /patients/{patient_id}/packet` with diagnostic-bearing errors.
 *
 * Mirrors what a plain typed query would do but throws `PacketLoadError`
 * instead of swallowing the response status, so the QueryClient's retry policy
 * can skip 4xx and the page can render the real cause (401? 404? network?).
 * The body is untyped in the OpenAPI schema, so it is cast to `DecisionPacket`.
 */
export function usePacket(patientId: string, enabled = true) {
  return useQuery<DecisionPacket, PacketLoadError>({
    queryKey: packetQueryKey(patientId),
    enabled: enabled && patientId.length > 0,
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
      return data as unknown as DecisionPacket;
    },
    retry: (failureCount, err) => {
      if (err instanceof PacketLoadError && isNonRetryableStatus(err.diag.status)) {
        return false;
      }
      return failureCount < 3;
    },
  });
}

/**
 * Fetch a resolvable evidence snippet via `GET /evidence/{evidence_id}`.
 */
export function useEvidence(evidenceId: string, enabled = true) {
  return useQuery<EvidenceSnippet>({
    queryKey: ["evidence", evidenceId],
    enabled: enabled && evidenceId.length > 0,
    queryFn: async () => {
      const { data, error, response } = await apiClient.GET(
        "/evidence/{evidence_id}",
        { params: { path: { evidence_id: evidenceId } } },
      );
      if (error !== undefined || !data) {
        throw new Error(
          `Failed to load evidence: HTTP ${statusOf(response)}`,
        );
      }
      return data as unknown as EvidenceSnippet;
    },
  });
}

/**
 * Fetch a raw FHIR resource (the citation target) via
 * `GET /patients/{patient_id}/resource/{resource_type}/{resource_id}`.
 * The body is arbitrary FHIR JSON, returned as `unknown`.
 */
export function useResource(
  patientId: string,
  resourceType: string,
  resourceId: string,
  enabled = true,
) {
  return useQuery<unknown>({
    queryKey: ["resource", patientId, resourceType, resourceId],
    enabled:
      enabled &&
      patientId.length > 0 &&
      resourceType.length > 0 &&
      resourceId.length > 0,
    queryFn: async () => {
      const { data, error, response } = await apiClient.GET(
        "/patients/{patient_id}/resource/{resource_type}/{resource_id}",
        {
          params: {
            path: {
              patient_id: patientId,
              resource_type: resourceType,
              resource_id: resourceId,
            },
          },
        },
      );
      if (error !== undefined || !data) {
        throw new Error(
          `Failed to load resource: HTTP ${statusOf(response)}`,
        );
      }
      return data as unknown;
    },
  });
}

/**
 * List registered connectors via `GET /connectors`.
 */
export function useConnectors() {
  return useQuery<Record<string, unknown>[]>({
    queryKey: ["connectors"],
    queryFn: async () => {
      const { data, error, response } = await apiClient.GET("/connectors");
      if (error !== undefined || !data) {
        throw new Error(
          `Failed to load connectors: HTTP ${statusOf(response)}`,
        );
      }
      return data as Record<string, unknown>[];
    },
  });
}

/**
 * Read the immutable audit log via `GET /audit`, newest first. The body is
 * untyped in the schema, so it is cast to `AuditEvent[]`.
 */
export function useAudit(limit?: number) {
  return useQuery<AuditEvent[]>({
    queryKey: ["audit", limit ?? null],
    queryFn: async () => {
      const { data, error, response } = await apiClient.GET("/audit", {
        params: { query: limit !== undefined ? { limit } : undefined },
      });
      if (error !== undefined || !data) {
        throw new Error(
          `Failed to load audit log: HTTP ${statusOf(response)}`,
        );
      }
      return data as unknown as AuditEvent[];
    },
  });
}

/**
 * Backend liveness via `GET /health`.
 */
export function useHealth() {
  return useQuery<Record<string, string>>({
    queryKey: ["health"],
    queryFn: async () => {
      const { data, error, response } = await apiClient.GET("/health");
      if (error !== undefined || !data) {
        throw new Error(
          `Health check failed: HTTP ${statusOf(response)}`,
        );
      }
      return data;
    },
  });
}

/* -------------------------------------------------------------------------- */
/* Mutations                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * Confirm a hypothesis via `POST /hypotheses/{id}/confirm`. Invalidates the
 * patient's packet on success so the UI reflects the new status.
 */
export function useConfirmHypothesis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: string; patientId: string }) => {
      const { data, error, response } = await apiClient.POST(
        "/hypotheses/{id}/confirm",
        {
          params: { path: { id: vars.id } },
          body: { patient_id: vars.patientId },
        },
      );
      if (error !== undefined || !data) {
        throw new Error(
          `Failed to confirm hypothesis: HTTP ${statusOf(response)}`,
        );
      }
      return data;
    },
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({
        queryKey: packetQueryKey(vars.patientId),
      });
    },
  });
}

/**
 * Dismiss a hypothesis via `POST /hypotheses/{id}/dismiss`. Invalidates the
 * patient's packet on success.
 */
export function useDismissHypothesis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: string; patientId: string }) => {
      const { data, error, response } = await apiClient.POST(
        "/hypotheses/{id}/dismiss",
        {
          params: { path: { id: vars.id } },
          body: { patient_id: vars.patientId },
        },
      );
      if (error !== undefined || !data) {
        throw new Error(
          `Failed to dismiss hypothesis: HTTP ${statusOf(response)}`,
        );
      }
      return data;
    },
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({
        queryKey: packetQueryKey(vars.patientId),
      });
    },
  });
}

/**
 * Trigger a TTL cache refresh via `POST /patients/{patient_id}/refresh`.
 * Invalidates the patient's packet on success.
 */
export function useRefreshPatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { patientId: string }) => {
      const { data, error, response } = await apiClient.POST(
        "/patients/{patient_id}/refresh",
        { params: { path: { patient_id: vars.patientId } } },
      );
      if (error !== undefined || !data) {
        throw new Error(
          `Failed to refresh patient: HTTP ${statusOf(response)}`,
        );
      }
      return data;
    },
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({
        queryKey: packetQueryKey(vars.patientId),
      });
    },
  });
}

/**
 * Ingest a patient from a connector via `POST /intake`. Invalidates the patient
 * list and the resulting patient's packet on success.
 */
export function useIntake() {
  const queryClient = useQueryClient();
  return useMutation<IntakeResponse, Error, IntakeRequest>({
    mutationFn: async (body: IntakeRequest) => {
      const { data, error, response } = await apiClient.POST("/intake", {
        body,
      });
      if (error !== undefined || !data) {
        throw new Error(
          `Failed to run intake: HTTP ${statusOf(response)}`,
        );
      }
      return data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["patients"] });
      if (data?.patient_id) {
        void queryClient.invalidateQueries({
          queryKey: packetQueryKey(data.patient_id),
        });
      }
    },
  });
}
