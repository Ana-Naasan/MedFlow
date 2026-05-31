"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "./api";
import { PacketLoadError } from "./usePacket";

/**
 * Fetch a single FHIR resource for a patient. Used by the Profile tab
 * (`Patient/{patient_id}`) and could be reused for any other resource type
 * (Condition / MedicationStatement / etc.) as those tabs come online.
 *
 * The diagnostic-bearing ``PacketLoadError`` is reused so the retry-skip
 * predicate in providers.tsx applies uniformly.
 */
export function usePatientResource(
  patientId: string,
  resourceType: string,
  resourceId: string,
) {
  return useQuery({
    queryKey: ["patient-resource", patientId, resourceType, resourceId],
    queryFn: async () => {
      const start = performance.now();
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
