import { describe, expect, it } from "vitest";

import type { paths } from "../lib/api/generated";

/**
 * Typed-surface tests for the intake and hypothesis route shapes.
 * No runtime behaviour — each assignment is a compile-time type assertion.
 * If a path or field is removed from the generated schema, this file fails tsc.
 */
describe("intake route types", () => {
  it("POST /intake body requires connector and source_patient_id", () => {
    type IntakeBody =
      paths["/intake"]["post"]["requestBody"]["content"]["application/json"];
    const body: IntakeBody = {
      connector: "mock-fhir",
      source_patient_id: "DEMO-001",
    };
    expect(body.connector).toBe("mock-fhir");
    expect(body.source_patient_id).toBe("DEMO-001");
  });

  it("POST /intake body accepts optional patient_id override", () => {
    type IntakeBody =
      paths["/intake"]["post"]["requestBody"]["content"]["application/json"];
    const withOverride: IntakeBody = {
      connector: "mock-fhir",
      source_patient_id: "DEMO-001",
      patient_id: "explicit-id",
    };
    expect(withOverride.patient_id).toBe("explicit-id");
  });

  it("POST /intake 201 response includes patient_id and hypothesis_ids", () => {
    type IntakeResponse =
      paths["/intake"]["post"]["responses"]["201"]["content"]["application/json"];
    const resp: IntakeResponse = {
      patient_id: "p-123",
      status: "registered",
      resource_count: 9,
      hypothesis_ids: ["hyp-1", "hyp-2"],
    };
    expect(resp.patient_id).toBe("p-123");
    expect(resp.hypothesis_ids).toHaveLength(2);
  });

  it("POST /hypotheses/{id}/confirm body requires patient_id", () => {
    type ConfirmBody =
      paths["/hypotheses/{id}/confirm"]["post"]["requestBody"]["content"]["application/json"];
    const body: ConfirmBody = { patient_id: "pat-001" };
    expect(body.patient_id).toBe("pat-001");
  });

  it("POST /hypotheses/{id}/dismiss response includes dismissed_ids", () => {
    type DismissResponse =
      paths["/hypotheses/{id}/dismiss"]["post"]["responses"]["200"]["content"]["application/json"];
    const resp: DismissResponse = {
      id: "hyp-1",
      status: "dismissed",
      dismissed_ids: ["hyp-1", "hyp-2", "hyp-3"],
    };
    expect(resp.dismissed_ids).toHaveLength(3);
  });
});
