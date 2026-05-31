// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../lib/api", () => ({
  apiClient: { GET: vi.fn() },
}));

import { apiClient } from "../lib/api";
import { PacketLoadError } from "../lib/usePacket";
import { usePatientResource } from "../lib/usePatientResource";

function wrap() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "TestQueryWrapper";
  return Wrapper;
}

describe("usePatientResource", () => {
  it("calls the typed resource endpoint with the path params", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: { resourceType: "Patient", id: "pat-001" },
      error: undefined,
      response: { status: 200, url: "" },
    } as never);
    const { result } = renderHook(
      () => usePatientResource("pat-001", "Patient", "pat-001"),
      { wrapper: wrap() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.GET).toHaveBeenCalledWith(
      "/patients/{patient_id}/resource/{resource_type}/{resource_id}",
      expect.objectContaining({
        params: {
          path: {
            patient_id: "pat-001",
            resource_type: "Patient",
            resource_id: "pat-001",
          },
        },
      }),
    );
  });

  it("throws a PacketLoadError on 404 carrying the body", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: undefined,
      error: { detail: "Citation not found" },
      response: { status: 404, url: "http://x/foo" },
    } as never);
    const { result } = renderHook(
      () => usePatientResource("nope", "Patient", "nope"),
      { wrapper: wrap() },
    );
    await waitFor(() => expect(result.current.isError).toBe(true));
    if (result.current.error instanceof PacketLoadError) {
      expect(result.current.error.diag.status).toBe(404);
      expect(result.current.error.diag.body).toEqual({
        detail: "Citation not found",
      });
    }
  });
});
