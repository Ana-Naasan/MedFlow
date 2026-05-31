import { describe, expect, it } from "vitest";

import type { paths } from "../lib/api/generated";

describe("intake form — typed API surface", () => {
  it("POST /intake accepts the required body shape", () => {
    type IntakeBody =
      paths["/intake"]["post"]["requestBody"]["content"]["application/json"];

    // Verify the required fields exist as strings in the type
    const body: IntakeBody = {
      connector: "mock-fhir",
      source_patient_id: "DEMO-001",
    };

    expect(body.connector).toBe("mock-fhir");
    expect(body.source_patient_id).toBe("DEMO-001");
  });

  it("POST /intake allows an optional patient_id", () => {
    type IntakeBody =
      paths["/intake"]["post"]["requestBody"]["content"]["application/json"];

    const withId: IntakeBody = {
      connector: "mock-fhir",
      source_patient_id: "DEMO-001",
      patient_id: "our-pat-001",
    };

    expect(withId.patient_id).toBe("our-pat-001");
  });

  it("POST /intake 201 response includes patient_id and hypothesis_ids", () => {
    type IntakeResp =
      paths["/intake"]["post"]["responses"]["201"]["content"]["application/json"];

    const resp: IntakeResp = {
      patient_id: "p-123",
      status: "registered",
      resource_count: 2,
      hypothesis_ids: ["h-1", "h-2"],
    };

    expect(resp.patient_id).toBe("p-123");
    expect(resp.hypothesis_ids).toHaveLength(2);
  });

  it("POST /hypotheses/{id}/confirm accepts patient_id body", () => {
    type ConfirmBody =
      paths["/hypotheses/{id}/confirm"]["post"]["requestBody"]["content"]["application/json"];

    const body: ConfirmBody = { patient_id: "pat-001" };
    expect(body.patient_id).toBe("pat-001");
  });

  it("POST /hypotheses/{id}/dismiss response includes dismissed_ids", () => {
    type DismissResp =
      paths["/hypotheses/{id}/dismiss"]["post"]["responses"]["200"]["content"]["application/json"];

    const resp: DismissResp = {
      id: "hyp-1",
      status: "dismissed",
      dismissed_ids: ["hyp-1", "hyp-2"],
    };

    expect(resp.dismissed_ids).toHaveLength(2);
  });
});
