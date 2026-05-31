"use client";

import { useCallback, useRef, useState } from "react";

import { apiClient } from "../lib/api";
import type { DecisionPacket } from "../lib/types";
import { PacketLoadError, usePacket } from "../lib/usePacket";
import { CompletenessIndicator } from "./CompletenessIndicator";
import { DataGapsBanner } from "./DataGapsBanner";
import { PacketLoadFailurePanel } from "./PacketLoadFailurePanel";
import { SuggestionCard } from "./SuggestionCard";

type ResolvedStatus = "confirmed" | "dismissed";

interface PacketViewProps {
  /** The patient ID whose DecisionPacket should be rendered. */
  patientId: string;
}

/**
 * The full provider decision-packet UI: data gaps banner, suggestion cards
 * with confirm/dismiss actions, completeness sidebar. Extracted from the
 * legacy /packet route so the new ``/patients/[id]/packet`` tab can mount
 * the same component with a per-patient id.
 */
export function PacketView({ patientId }: PacketViewProps) {
  const { data, isLoading, isError, error } = usePacket(patientId);

  const [resolved, setResolved] = useState<Record<string, ResolvedStatus>>({});
  const [acting, setActing] = useState<Set<string>>(() => new Set());
  const [actionError, setActionError] = useState<string | null>(null);
  const approveRefs = useRef<(HTMLButtonElement | null)[]>([]);

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
      alsoResolved?: Set<string>,
    ) => {
      for (let i = currentIdx + 1; i < hypotheses.length; i++) {
        const id = hypotheses[i].id;
        if (!resolvedRef.current[id] && !alsoResolved?.has(id)) {
          approveRefs.current[i]?.focus();
          return;
        }
      }
    },
    [],
  );

  const handleConfirm = useCallback(
    async (hypId: string, pid: string, idx: number, title: string) => {
      if (!packet || acting.has(hypId)) return;
      setActionError(null);
      beginAct(hypId);
      try {
        const { error: postError } = await apiClient.POST(
          "/hypotheses/{id}/confirm",
          {
            params: { path: { id: hypId } },
            body: { patient_id: pid },
          },
        );
        if (postError) {
          setActionError(`Could not approve "${title}". Please try again.`);
          return;
        }
        setResolved((prev) => ({ ...prev, [hypId]: "confirmed" }));
        focusNext(idx, packet.hypotheses);
      } catch {
        setActionError(
          `Could not approve "${title}" — a network error occurred. Please try again.`,
        );
      } finally {
        endAct(hypId);
      }
    },
    [packet, acting, beginAct, endAct, focusNext],
  );

  const handleDismiss = useCallback(
    async (hypId: string, pid: string, idx: number, title: string) => {
      if (!packet || acting.has(hypId)) return;
      setActionError(null);
      beginAct(hypId);
      try {
        const { data: resp, error: postError } = await apiClient.POST(
          "/hypotheses/{id}/dismiss",
          {
            params: { path: { id: hypId } },
            body: { patient_id: pid },
          },
        );
        if (postError) {
          setActionError(`Could not dismiss "${title}". Please try again.`);
          return;
        }
        const dismissedIds =
          resp && resp.dismissed_ids.length > 0
            ? resp.dismissed_ids
            : [hypId];
        const dismissedSet = new Set(dismissedIds);
        setResolved((prev) => {
          const next = { ...prev };
          for (const id of dismissedIds) next[id] = "dismissed";
          return next;
        });
        focusNext(idx, packet.hypotheses, dismissedSet);
      } catch {
        setActionError(
          `Could not dismiss "${title}" — a network error occurred. Please try again.`,
        );
      } finally {
        endAct(hypId);
      }
    },
    [packet, acting, beginAct, endAct, focusNext],
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
    const diag =
      error instanceof PacketLoadError
        ? error.diag
        : { status: undefined, body: null, url: "", elapsedMs: 0 };
    return <PacketLoadFailurePanel diag={diag} />;
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
                    hypothesis.title,
                  )
                }
                onDismiss={() =>
                  handleDismiss(
                    hypothesis.id,
                    packet!.patient_id,
                    idx,
                    hypothesis.title,
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
