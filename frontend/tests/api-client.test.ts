import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { $api, apiClient, bearerMiddleware } from "../lib/api/client";
import type { paths } from "../lib/api/generated";

describe("api client", () => {
  it("exposes GET and POST methods", () => {
    expect(typeof apiClient.GET).toBe("function");
    expect(typeof apiClient.POST).toBe("function");
  });

  it("is typed for the live patient routes", () => {
    // Verifies the regenerated typed client surface covers the live API.
    // Each key would be a type error if the path were absent from the
    // generated schema, so referencing them proves the types exist.
    type PatientsGet = paths["/patients"]["get"];
    type PacketGet = paths["/patients/{patient_id}/packet"]["get"];
    type CitationGet = paths["/patients/{patient_id}/resource/{resource_type}/{resource_id}"]["get"];
    type RefreshPost = paths["/patients/{patient_id}/refresh"]["post"];
    const surface: Record<string, boolean> = {
      patients: (null as unknown as PatientsGet) === null,
      packet: (null as unknown as PacketGet) === null,
      citation: (null as unknown as CitationGet) === null,
      refresh: (null as unknown as RefreshPost) === null,
    };
    expect(Object.keys(surface)).toHaveLength(4);
  });

  it("is typed for the connectors and evidence routes", () => {
    type ConnectorsGet = paths["/connectors"]["get"];
    type EvidenceGet = paths["/evidence/{evidence_id}"]["get"];
    const surface: Record<string, boolean> = {
      connectors: (null as unknown as ConnectorsGet) === null,
      evidence: (null as unknown as EvidenceGet) === null,
    };
    expect(Object.keys(surface)).toHaveLength(2);
  });

  it("is typed for intake and hypothesis routes", () => {
    type IntakePost = paths["/intake"]["post"];
    type ConfirmPost = paths["/hypotheses/{id}/confirm"]["post"];
    type DismissPost = paths["/hypotheses/{id}/dismiss"]["post"];
    const surface: Record<string, boolean> = {
      intake: (null as unknown as IntakePost) === null,
      confirm: (null as unknown as ConfirmPost) === null,
      dismiss: (null as unknown as DismissPost) === null,
    };
    expect(Object.keys(surface)).toHaveLength(3);
  });

  it("is typed for the health route", () => {
    type HealthGet = paths["/health"]["get"];
    const present = (null as unknown as HealthGet) === null;
    expect(present).toBe(true);
  });
});

describe("bearer middleware", () => {
  const originalToken = process.env.NEXT_PUBLIC_API_TOKEN;

  // Minimal stub for the openapi-fetch onRequest callback params; only `request`
  // is exercised here, so the remaining fields carry placeholder values.
  function callOnRequest(request: Request): Request {
    const result = bearerMiddleware.onRequest!({
      request,
      schemaPath: "/health",
      params: {},
      id: "test-request",
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      options: {} as any,
    });
    return result as Request;
  }

  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_API_TOKEN;
  });

  afterEach(() => {
    if (originalToken === undefined) {
      delete process.env.NEXT_PUBLIC_API_TOKEN;
    } else {
      process.env.NEXT_PUBLIC_API_TOKEN = originalToken;
    }
  });

  it("injects the Authorization header when the token is set at request time", () => {
    process.env.NEXT_PUBLIC_API_TOKEN = "test-token";
    const request = new Request("http://localhost:8000/health");
    const result = callOnRequest(request);
    expect(result.headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("omits the Authorization header when the token is unset", () => {
    delete process.env.NEXT_PUBLIC_API_TOKEN;
    const request = new Request("http://localhost:8000/health");
    const result = callOnRequest(request);
    expect(result.headers.get("Authorization")).toBeNull();
  });
});

describe("openapi-react-query wiring", () => {
  it("exposes $api with a useQuery hook function", () => {
    expect(typeof $api.useQuery).toBe("function");
  });
});
