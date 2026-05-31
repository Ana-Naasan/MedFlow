"use client";

import { useCallback, useRef, useState } from "react";
import { SuggestionCard } from "../../../components/SuggestionCard";
import { $api, apiClient } from "../../../lib/api";
import type { DecisionPacket } from "../../../lib/types";

type ResolvedStatus = "confirmed" | "dismissed";

export default function ProviderPacketPage() {
  const { data, isLoading, isError } = $api.useQuery(
    "get",
    "/patients/{patient_id}/packet",
    { params: { path: { patient_id: "pat-001" } } }
  );

  const [resolved, setResolved] = useState<Record<string, ResolvedStatus>>({});
  const [acting, setActing] = useState<string | null>(null);
  const approveRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const packet = data as unknown as DecisionPacket | undefined;

  const focusNext = useCallback(
    (currentIdx: number, hypotheses: DecisionPacket["hypotheses"]) => {
      for (let i = currentIdx + 1; i < hypotheses.length; i++) {
        if (!resolved[hypotheses[i].id]) {
          approveRefs.current[i]?.focus();
          return;
        }
      }
    },
    [resolved]
  );

  const handleConfirm = useCallback(
    async (hypId: string, patientId: string, idx: number) => {
      if (!packet) return;
      setActing(hypId);
      try {
        await apiClient.POST("/hypotheses/{id}/confirm", {
          params: { path: { id: hypId } },
          body: { patient_id: patientId },
        });
        setResolved((prev) => ({ ...prev, [hypId]: "confirmed" }));
        focusNext(idx, packet.hypotheses);
      } finally {
        setActing(null);
      }
    },
    [packet, focusNext]
  );

  const handleDismiss = useCallback(
    async (hypId: string, patientId: string, idx: number) => {
      if (!packet) return;
      setActing(hypId);
      try {
        await apiClient.POST("/hypotheses/{id}/dismiss", {
          params: { path: { id: hypId } },
          body: { patient_id: patientId },
        });
        setResolved((prev) => ({ ...prev, [hypId]: "dismissed" }));
        focusNext(idx, packet.hypotheses);
      } finally {
        setActing(null);
      }
    },
    [packet, focusNext]
  );

  if (isLoading) {
    return (
      <main>
        <div className="shell">
          <p>Loading packet…</p>
        </div>
      </main>
    );
  }

  if (isError || !data) {
    return (
      <main>
        <div className="shell">
          <p>Failed to load packet.</p>
        </div>
      </main>
    );
  }

  return (
    <main>
      <div className="shell">
        <section className="stack" aria-label="Hypothesis review">
          {packet!.hypotheses.map((hypothesis, idx) => (
            <SuggestionCard
              key={hypothesis.id}
              hypothesis={hypothesis}
              patientId={packet!.patient_id}
              status={resolved[hypothesis.id] ?? null}
              isActing={acting === hypothesis.id}
              approveRef={(el) => {
                approveRefs.current[idx] = el;
              }}
              onConfirm={() => handleConfirm(hypothesis.id, packet!.patient_id, idx)}
              onDismiss={() => handleDismiss(hypothesis.id, packet!.patient_id, idx)}
            />
          ))}
        </section>
      </div>
    </main>
  );
}
