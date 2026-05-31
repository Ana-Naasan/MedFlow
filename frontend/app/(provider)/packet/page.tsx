"use client";

import { CompletenessIndicator } from "../../../components/CompletenessIndicator";
import { SuggestionCard } from "../../../components/SuggestionCard";
import { $api } from "../../../lib/api";
import type { DecisionPacket } from "../../../lib/types";

export default function ProviderPacketPage() {
  const { data, isLoading, isError } = $api.useQuery(
    "get",
    "/patients/{patient_id}/packet",
    { params: { path: { patient_id: "pat-001" } } }
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

  const packet = data as unknown as DecisionPacket;
  const completeness = packet.completeness ?? [];

  return (
    <main>
      <div className="shell">
        <div className="packet-layout">
          <section className="stack">
            {packet.hypotheses.map((hypothesis) => (
              <SuggestionCard
                key={hypothesis.id}
                hypothesis={hypothesis}
                patientId={packet.patient_id}
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
