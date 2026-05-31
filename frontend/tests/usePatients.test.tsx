// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../lib/api", () => ({
  apiClient: { GET: vi.fn() },
}));

import { apiClient } from "../lib/api";
import { PacketLoadError } from "../lib/usePacket";
import { usePatients } from "../lib/usePatients";

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

describe("usePatients", () => {
  it("returns the patient list on success", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: [{ id: "pat-001" }, { id: "DEMO-001" }],
      error: undefined,
      response: { status: 200, url: "" },
    } as never);
    const { result } = renderHook(() => usePatients(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([{ id: "pat-001" }, { id: "DEMO-001" }]);
  });

  it("throws a PacketLoadError carrying the diagnostic info on failure", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: undefined,
      error: { detail: "Missing bearer token" },
      response: { status: 401, url: "http://x/patients" },
    } as never);
    const { result } = renderHook(() => usePatients(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    const err = result.current.error;
    expect(err).toBeInstanceOf(PacketLoadError);
    if (err instanceof PacketLoadError) {
      expect(err.diag.status).toBe(401);
      expect(err.diag.url).toBe("http://x/patients");
      expect(err.diag.body).toEqual({ detail: "Missing bearer token" });
    }
  });

  it("treats missing data without error as a no-response failure", async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: undefined,
      error: undefined,
      response: undefined,
    } as never);
    const { result } = renderHook(() => usePatients(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    if (result.current.error instanceof PacketLoadError) {
      expect(result.current.error.diag.status).toBeUndefined();
    }
  });
});
