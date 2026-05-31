// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/api", () => ({
  $api: { useQuery: vi.fn() },
}));

import { $api } from "../lib/api";
import { CitationChip } from "../components/CitationChip";
import type { Citation } from "../lib/types";

const evidenceCitation: Citation = {
  kind: "evidence",
  ref: "ddinter-aspirin-warfarin",
  label: "DDInter aspirin-warfarin",
};

const resourceCitation: Citation = {
  kind: "resource",
  ref: "Patient/pat-001",
  label: "Patient/pat-001",
};

const mockIdle = { data: undefined, isLoading: false, isError: false };

describe("CitationChip", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked($api.useQuery).mockReturnValue(mockIdle as never);
  });

  // ── Chip rendering ──────────────────────────────────────────────────────

  it("renders chip label", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    expect(
      screen.getByRole("button", { name: /DDInter aspirin-warfarin/i })
    ).toBeInTheDocument();
  });

  it("uses citation ref when label is null", () => {
    const nullLabel: Citation = { ...evidenceCitation, label: null };
    render(<CitationChip citation={nullLabel} patientId="pat-001" />);
    expect(
      screen.getByRole("button", { name: /ddinter-aspirin-warfarin/i })
    ).toBeInTheDocument();
  });

  // ── Visual distinction ──────────────────────────────────────────────────

  it("renders knowledge chip with correct visual style", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    const chip = screen.getByRole("button", { name: /DDInter aspirin-warfarin/i });
    expect(chip.className).toContain("chip-knowledge");
  });

  it("renders patient-fact chip with correct visual style", () => {
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    const chip = screen.getByRole("button", { name: /Patient\/pat-001/i });
    expect(chip.className).toContain("chip-patient-fact");
  });

  it("knowledge chip has data-citation-type knowledge", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    const chip = screen.getByRole("button", { name: /DDInter aspirin-warfarin/i });
    expect(chip).toHaveAttribute("data-citation-type", "knowledge");
  });

  it("patient-fact chip has data-citation-type patient-fact", () => {
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    const chip = screen.getByRole("button", { name: /Patient\/pat-001/i });
    expect(chip).toHaveAttribute("data-citation-type", "patient-fact");
  });

  // ── Knowledge chip interaction ──────────────────────────────────────────

  it("knowledge chip tap opens EvidencePanel", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    expect(screen.queryByTestId("evidence-panel")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /DDInter aspirin-warfarin/i }));
    expect(screen.getByTestId("evidence-panel")).toBeInTheDocument();
  });

  it("knowledge chip tap calls GET /evidence/{id}", () => {
    const mockEvidenceData = {
      data: { snippet: "Aspirin and warfarin may increase bleeding risk.", source: "DDInter" },
      isLoading: false,
      isError: false,
    };
    vi.mocked($api.useQuery).mockReturnValue(mockEvidenceData as never);
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: /DDInter aspirin-warfarin/i }));
    const calls = vi.mocked($api.useQuery).mock.calls;
    const evidenceCall = calls.find((c) => c[1] === "/evidence/{evidence_id}");
    expect(evidenceCall).toBeDefined();
    expect(
      (evidenceCall![2] as unknown as { params: { path: { evidence_id: string } } }).params.path
        .evidence_id
    ).toBe("ddinter-aspirin-warfarin");
  });

  it("EvidencePanel close button dismisses the panel", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: /DDInter aspirin-warfarin/i }));
    expect(screen.getByTestId("evidence-panel")).toBeInTheDocument();
    // Close button is inside the panel
    fireEvent.click(screen.getAllByRole("button", { name: /close/i })[0]);
    expect(screen.queryByTestId("evidence-panel")).not.toBeInTheDocument();
  });

  // ── Patient-fact chip interaction ────────────────────────────────────────

  it("patient-fact chip tap is safe no-op — no EvidencePanel opens", () => {
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: /Patient\/pat-001/i }));
    expect(screen.queryByTestId("evidence-panel")).not.toBeInTheDocument();
  });

  it("patient-fact chip tap does not call evidence API", () => {
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: /Patient\/pat-001/i }));
    const calls = vi.mocked($api.useQuery).mock.calls;
    const evidenceCall = calls.find((c) => c[1] === "/evidence/{evidence_id}");
    expect(evidenceCall).toBeUndefined();
  });
});
