// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Integration test for the provider packet page's review actions. The real
// SuggestionCard is rendered (NOT mocked) so the headline focus-management,
// confirm/dismiss, error-handling, and cascade logic are actually exercised —
// only the network client and the data query are stubbed.
const POST = vi.fn();
vi.mock("../lib/api", () => ({
  $api: { useQuery: vi.fn() },
  apiClient: { POST: (...args: unknown[]) => POST(...args) },
}));
vi.mock("../components/CitationChip", () => ({
  CitationChip: () => null,
}));

import { $api } from "../lib/api";
import Page from "../app/(provider)/packet/page";

const packet = {
  patient_id: "pat-001",
  summary_markdown: "",
  hypotheses: [
    {
      id: "hyp-1",
      title: "Bleeding risk",
      why: "Aspirin with warfarin.",
      severity: "high",
      confidence: "high",
      citations: [],
    },
    {
      id: "hyp-2",
      title: "Falls risk",
      why: "Sedating load.",
      severity: "moderate",
      confidence: "low",
      citations: [],
    },
  ],
  data_gaps: [],
  cache_status: "HIT",
};

beforeEach(() => {
  vi.mocked($api.useQuery).mockReturnValue({
    data: packet,
    isLoading: false,
    isError: false,
  } as never);
  POST.mockReset();
});

describe("ProviderPacketPage — review actions", () => {
  it("confirm POSTs the correct path+body and marks the card approved", async () => {
    POST.mockResolvedValue({ data: { id: "hyp-1", status: "confirmed" }, error: undefined });
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Approve: Bleeding risk" }));

    await waitFor(() =>
      expect(POST).toHaveBeenCalledWith("/hypotheses/{id}/confirm", {
        params: { path: { id: "hyp-1" } },
        body: { patient_id: "pat-001" },
      })
    );
    expect(await screen.findByText(/✓ Approved/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does NOT mark approved and surfaces an alert when the API returns an error", async () => {
    POST.mockResolvedValue({ data: undefined, error: { detail: "boom" } });
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Approve: Bleeding risk" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not approve/i);
    expect(screen.queryByText(/✓ Approved/)).not.toBeInTheDocument();
    // The Approve button is still present (action did not resolve the card).
    expect(
      screen.getByRole("button", { name: "Approve: Bleeding risk" })
    ).toBeInTheDocument();
  });

  it("does NOT mark approved and surfaces an alert when the request rejects (network)", async () => {
    POST.mockRejectedValue(new Error("network down"));
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Approve: Bleeding risk" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/network error/i);
    expect(screen.queryByText(/✓ Approved/)).not.toBeInTheDocument();
  });

  it("dismiss reflects every cascade id from dismissed_ids", async () => {
    POST.mockResolvedValue({
      data: { id: "hyp-1", status: "dismissed", dismissed_ids: ["hyp-1", "hyp-2"] },
      error: undefined,
    });
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Dismiss: Bleeding risk" }));

    const dismissed = await screen.findAllByText(/✗ Dismissed/);
    expect(dismissed).toHaveLength(2);
  });

  it("moves focus to the next unresolved card's Approve button after confirm", async () => {
    POST.mockResolvedValue({ data: { id: "hyp-1", status: "confirmed" }, error: undefined });
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Approve: Bleeding risk" }));

    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByRole("button", { name: "Approve: Falls risk" })
      )
    );
  });
});
