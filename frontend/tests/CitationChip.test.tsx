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

const resourceWithSpan: Citation = {
  kind: "resource",
  ref: "MedicationStatement/med-warfarin",
  label: "Warfarin (PDF)",
  source_span: {
    page: 2,
    start: 143,
    end: 183,
    snippet: "Warfarin 5 mg oral Anticoagulant Daily",
  },
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
    render(<CitationChip citation={resourceWithSpan} patientId="DEMO-001" />);
    const chip = screen.getByRole("button", { name: /Warfarin \(PDF\)/i });
    expect(chip.className).toContain("chip-patient-fact");
  });

  it("knowledge chip has data-citation-type knowledge", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    const chip = screen.getByRole("button", { name: /DDInter aspirin-warfarin/i });
    expect(chip).toHaveAttribute("data-citation-type", "knowledge");
  });

  it("patient-fact chip has data-citation-type patient-fact", () => {
    render(<CitationChip citation={resourceWithSpan} patientId="DEMO-001" />);
    const chip = screen.getByRole("button", { name: /Warfarin \(PDF\)/i });
    expect(chip).toHaveAttribute("data-citation-type", "patient-fact");
  });

  // ── Non-interactive patient-fact chip (no source_span) ───────────────────

  it("renders a span (not a button) when resource citation has no source_span", () => {
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    expect(
      screen.queryByRole("button", { name: /Patient\/pat-001/i })
    ).not.toBeInTheDocument();
    const chip = screen.getByText(/Patient\/pat-001/i);
    expect(chip.tagName).toBe("SPAN");
    expect(chip).toHaveAttribute("data-interactive", "false");
    expect(chip.className).toContain("chip-static");
    expect(chip.className).toContain("chip-patient-fact");
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

  // ── Patient-fact chip interaction (with source_span) ─────────────────────

  it("patient-fact chip with source_span opens the PdfHighlight panel", () => {
    render(<CitationChip citation={resourceWithSpan} patientId="DEMO-001" />);
    expect(screen.queryByTestId("pdf-highlight-panel")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Warfarin \(PDF\)/i }));
    expect(screen.getByTestId("pdf-highlight-panel")).toBeInTheDocument();
    expect(screen.getByTestId("pdf-highlight")).toBeInTheDocument();
    expect(screen.getByText("Warfarin 5 mg oral Anticoagulant Daily")).toBeInTheDocument();
  });

  it("patient-fact chip with source_span does not open the EvidencePanel", () => {
    render(<CitationChip citation={resourceWithSpan} patientId="DEMO-001" />);
    fireEvent.click(screen.getByRole("button", { name: /Warfarin \(PDF\)/i }));
    expect(screen.queryByTestId("evidence-panel")).not.toBeInTheDocument();
  });

  it("PdfHighlight panel close button dismisses the panel", () => {
    render(<CitationChip citation={resourceWithSpan} patientId="DEMO-001" />);
    fireEvent.click(screen.getByRole("button", { name: /Warfarin \(PDF\)/i }));
    expect(screen.getByTestId("pdf-highlight-panel")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /close/i })[0]);
    expect(screen.queryByTestId("pdf-highlight-panel")).not.toBeInTheDocument();
  });

  it("non-interactive patient-fact chip cannot open any panel", () => {
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByText(/Patient\/pat-001/i));
    expect(screen.queryByTestId("evidence-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("pdf-highlight-panel")).not.toBeInTheDocument();
    const calls = vi.mocked($api.useQuery).mock.calls;
    const evidenceCall = calls.find((c) => c[1] === "/evidence/{evidence_id}");
    expect(evidenceCall).toBeUndefined();
  });
});
