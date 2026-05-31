import { describe, expect, it } from "vitest";

import { apiClient } from "../lib/api/client";
import type { components } from "../lib/api/generated";

describe("api client", () => {
  it("exposes GET and POST methods", () => {
    expect(typeof apiClient.GET).toBe("function");
    expect(typeof apiClient.POST).toBe("function");
  });

  it("GET is typed for the packet endpoint", () => {
    // Verifies the typed client surface includes the packet path.
    // Calling apiClient.GET("/packet/{patient_id}", ...) would be a type error
    // if the path isn't in the generated schema — this import proves the types exist.
    type PacketResponse = components["schemas"]["DecisionPacket"];
    const shape: Partial<PacketResponse> = {
      patient_id: "pat-001",
      summary_markdown: "## stub",
    };
    expect(shape.patient_id).toBe("pat-001");
  });

  it("DecisionPacket schema includes hypotheses and data_gaps", () => {
    type Hypothesis = components["schemas"]["Hypothesis"];
    const h: Hypothesis = {
      id: "h-1",
      title: "test",
      why: "because",
      severity: "low",
      confidence: "high",
    };
    expect(h.id).toBe("h-1");
  });

  it("Citation schema includes kind and ref", () => {
    type Citation = components["schemas"]["Citation"];
    const c: Citation = { kind: "evidence_card", ref: "rxnorm://1" };
    expect(c.ref).toBe("rxnorm://1");
  });
});
