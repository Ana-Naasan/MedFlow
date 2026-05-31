"use client";

import { useCallback, useRef, useState } from "react";
import { CompletenessIndicator } from "../../../components/CompletenessIndicator";
import { DataGapsBanner } from "../../../components/DataGapsBanner";
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
  // In-flight action ids. A Set (not a single slot) so concurrent actions on
  // different cards don't re-enable each other early or admit a duplicate POST.
  const [acting, setActing] = useState<Set<string>>(() => new Set());
  const [actionError, setActionError] = useState<string | null>(null);
  const approveRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Mirror `resolved` into a ref so focusNext always reads the latest map
  // (avoids a stale closure when several siblings resolve in one cascade).
  const resolvedRef = useRef(resolved);
  resolvedRef.current = resolved;

  const packet = data as unknown as DecisionPacket | undefined;

  const beginAct = useCallback((id: string) => {
    setActing((prev) => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }, []);

  const endAct = useCallback((id: string) => {
    setActing((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const focusNext = useCallback(
    (
      currentIdx: number,
      hypotheses: DecisionPacket["hypotheses"],
      alsoResolved?: Set<string>
    ) => {
      for (let i = currentIdx + 1; i < hypotheses.length; i++) {
        const id = hypotheses[i].id;
        if (!resolvedRef.current[id] && !alsoResolved?.has(id)) {
          approveRefs.current[i]?.focus();
          return;
        }
      }
    },
    []
  );

  const handleConfirm = useCallback(
    async (hypId: string, patientId: string, idx: number, title: string) => {
      if (!packet || acting.has(hypId)) return;
      setActionError(null);
      beginAct(hypId);
      try {
        // openapi-fetch resolves { data, error } and does NOT throw on 4xx/5xx —
        // so a server rejection must be detected via `error`, never assumed success.
        const { error } = await apiClient.POST("/hypotheses/{id}/confirm", {
          params: { path: { id: hypId } },
          body: { patient_id: patientId },
        });
        if (error) {
          setActionError(`Could not approve "${title}". Please try again.`);
          return;
        }
        setResolved((prev) => ({ ...prev, [hypId]: "confirmed" }));
        focusNext(idx, packet.hypotheses);
      } catch {
        setActionError(
          `Could not approve "${title}" — a network error occurred. Please try again.`
        );
      } finally {
        endAct(hypId);
      }
    },
    [packet, acting, beginAct, endAct, focusNext]
  );

  const handleDismiss = useCallback(
    async (hypId: string, patientId: string, idx: number, title: string) => {
      if (!packet || acting.has(hypId)) return;
      setActionError(null);
      beginAct(hypId);
      try {
        const { data: resp, error } = await apiClient.POST(
          "/hypotheses/{id}/dismiss",
          {
            params: { path: { id: hypId } },
            body: { patient_id: patientId },
          }
        );
        if (error) {
          setActionError(`Could not dismiss "${title}". Please try again.`);
          return;
        }
        // The backend dismisses sibling hypotheses (same group); reflect every
        // returned id so cascaded siblings don't stay actionable until reload.
        const dismissedIds =
          resp && resp.dismissed_ids.length > 0 ? resp.dismissed_ids : [hypId];
        const dismissedSet = new Set(dismissedIds);
        setResolved((prev) => {
          const next = { ...prev };
          for (const id of dismissedIds) next[id] = "dismissed";
          return next;
        });
        focusNext(idx, packet.hypotheses, dismissedSet);
      } catch {
        setActionError(
          `Could not dismiss "${title}" — a network error occurred. Please try again.`
        );
      } finally {
        endAct(hypId);
      }
    },
    [packet, acting, beginAct, endAct, focusNext]
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

  const completeness = packet!.completeness ?? [];
  const dataGaps = packet!.data_gaps ?? [];

  return (
    <main>
      <div className="shell">
        {actionError && (
          <p role="alert" className="banner banner-error">
            {actionError}
          </p>
        )}
        <DataGapsBanner gaps={dataGaps} />
        <div className="packet-layout">
          <section className="stack" aria-label="Hypothesis review">
            {packet!.hypotheses.map((hypothesis, idx) => (
              <SuggestionCard
                key={hypothesis.id}
                hypothesis={hypothesis}
                patientId={packet!.patient_id}
                status={resolved[hypothesis.id] ?? null}
                isActing={acting.has(hypothesis.id)}
                approveRef={(el) => {
                  approveRefs.current[idx] = el;
                }}
                onConfirm={() =>
                  handleConfirm(
                    hypothesis.id,
                    packet!.patient_id,
                    idx,
                    hypothesis.title
                  )
                }
                onDismiss={() =>
                  handleDismiss(
                    hypothesis.id,
                    packet!.patient_id,
                    idx,
                    hypothesis.title
                  )
                }
              />
            ))}
          </section>
          {completeness.length > 0 && (
            <CompletenessIndicator completeness={completeness} />
          )}
        </div>
      </div>
    </main>
  );
}
