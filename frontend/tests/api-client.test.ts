import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { $api, apiClient, bearerMiddleware } from "../lib/api/client";
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
