// @vitest-environment jsdom

import { fireEvent, render, screen, within } from "@testing-library/react";
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
const mockLoading = { data: undefined, isLoading: true, isError: false };
const mockError = { data: undefined, isLoading: false, isError: true };
const mockEvidenceData = {
  data: { snippet: "Aspirin and warfarin may increase bleeding risk.", source: "DDInter" },
  isLoading: false,
  isError: false,
};
const mockEvidenceWithUrl = {
  data: {
    snippet: "Aspirin and warfarin may increase bleeding risk.",
    source: "DDInter",
    ref_url: "https://ddinter.scbdd.com/",
  },
  isLoading: false,
  isError: false,
};
const mockResourceData = {
  data: { resourceType: "Patient", id: "pat-001", gender: "female" },
  isLoading: false,
  isError: false,
};
const mockResourceWithSpan = {
  data: {
    resourceType: "MedicationStatement",
    id: "med-warfarin",
    span: { page: 2, start: 143, end: 183, snippet: "Warfarin 5 mg oral Anticoagulant Daily" },
  },
  isLoading: false,
  isError: false,
};

const pdfCitation: Citation = {
  kind: "resource",
  ref: "MedicationStatement/med-warfarin",
  label: "Warfarin (PDF)",
};

describe("CitationChip", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked($api.useQuery).mockReturnValue(mockIdle as never);
  });

  it("renders chip label", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    expect(
      screen.getByRole("button", { name: "DDInter aspirin-warfarin" })
    ).toBeInTheDocument();
  });

  it("uses citation ref when label is null — chip and modal source both show ref", () => {
    const nullLabel: Citation = { ...evidenceCitation, label: null };
    render(<CitationChip citation={nullLabel} patientId="pat-001" />);
    expect(
      screen.getByRole("button", { name: "ddinter-aspirin-warfarin" })
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "ddinter-aspirin-warfarin" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("ddinter-aspirin-warfarin")).toBeInTheDocument();
  });

  it("click opens the modal dialog", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows snippet after click for evidence citation", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockEvidenceData as never);
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(
      screen.getByText("Aspirin and warfarin may increase bleeding risk.")
    ).toBeInTheDocument();
  });

  it("resolves evidence citation via /evidence endpoint", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockEvidenceData as never);
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    const calls = vi.mocked($api.useQuery).mock.calls;
    const evidenceCall = calls.find((c) => c[1] === "/evidence/{evidence_id}");
    expect(evidenceCall).toBeDefined();
    expect(
      (evidenceCall![2] as unknown as { params: { path: { evidence_id: string } } }).params.path
        .evidence_id
    ).toBe("ddinter-aspirin-warfarin");
  });

  it("resolves resource citation via /resource endpoint", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockResourceData as never);
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "Patient/pat-001" }));
    const calls = vi.mocked($api.useQuery).mock.calls;
    const resourceCall = calls.find(
      (c) => c[1] === "/patients/{patient_id}/resource/{resource_type}/{resource_id}"
    );
    expect(resourceCall).toBeDefined();
    const params = (
      resourceCall![2] as unknown as {
        params: { path: { resource_type: string; resource_id: string } };
      }
    ).params.path;
    expect(params.resource_type).toBe("Patient");
    expect(params.resource_id).toBe("pat-001");
  });

  it("shows skeleton loading state while fetching", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockLoading as never);
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows error message on fetch failure", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockError as never);
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });

  it("shows resource id fallback when response has no snippet", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockResourceData as never);
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "Patient/pat-001" }));
    expect(screen.getByText("Resource: pat-001")).toBeInTheDocument();
  });

  it("shows 'Source not found' when response has no snippet and no id", () => {
    vi.mocked($api.useQuery).mockReturnValue({
      data: { resourceType: "Patient" },
      isLoading: false,
      isError: false,
    } as never);
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "Patient/pat-001" }));
    expect(screen.getByText("Source not found.")).toBeInTheDocument();
  });

  it("close button hides the modal", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("backdrop click closes the modal", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("modal-backdrop"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("Escape key closes the modal", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows PDF highlight view when resource has span data", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockResourceWithSpan as never);
    render(<CitationChip citation={pdfCitation} patientId="DEMO-001" />);
    fireEvent.click(screen.getByRole("button", { name: "Warfarin (PDF)" }));
    expect(screen.getByTestId("pdf-highlight")).toBeInTheDocument();
    expect(screen.getByText("Warfarin 5 mg oral Anticoagulant Daily")).toBeInTheDocument();
    expect(screen.getByText(/PDF · Page 2/i)).toBeInTheDocument();
  });

  it("shows plain snippet when resource has no span", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockEvidenceData as never);
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.queryByTestId("pdf-highlight")).not.toBeInTheDocument();
    expect(
      screen.getByText("Aspirin and warfarin may increase bleeding risk.")
    ).toBeInTheDocument();
  });

  // --- Issue #25: knowledge-citation evidence side panel ---

  it("knowledge chip uses the chip-knowledge variant class", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    const chip = screen.getByRole("button", { name: "DDInter aspirin-warfarin" });
    expect(chip).toHaveClass("chip-knowledge");
    expect(chip).not.toHaveClass("chip-resource");
  });

  it("patient-fact chip uses the chip-resource variant class", () => {
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    const chip = screen.getByRole("button", { name: "Patient/pat-001" });
    expect(chip).toHaveClass("chip-resource");
    expect(chip).not.toHaveClass("chip-knowledge");
  });

  it("renders the citation detail as a side panel", () => {
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.getByRole("dialog")).toHaveClass("citation-panel");
  });

  it("knowledge panel renders an outbound source link to ref_url", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockEvidenceWithUrl as never);
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    const link = screen.getByRole("link", { name: /view source/i });
    expect(link).toHaveAttribute("href", "https://ddinter.scbdd.com/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel") ?? "").toContain("noopener");
  });

  it("knowledge panel omits the source link when ref_url is absent", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockEvidenceData as never);
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.queryByRole("link", { name: /view source/i })).not.toBeInTheDocument();
    expect(
      screen.getByText("Aspirin and warfarin may increase bleeding risk.")
    ).toBeInTheDocument();
  });

  it("patient-fact panel has no outbound source link", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockResourceData as never);
    render(<CitationChip citation={resourceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "Patient/pat-001" }));
    expect(screen.queryByRole("link", { name: /view source/i })).not.toBeInTheDocument();
  });

  it("does not render a link for a non-http ref_url (scheme guard)", () => {
    vi.mocked($api.useQuery).mockReturnValue({
      data: { snippet: "x", source: "DDInter", ref_url: "javascript:alert(1)" },
      isLoading: false,
      isError: false,
    } as never);
    render(<CitationChip citation={evidenceCitation} patientId="pat-001" />);
    fireEvent.click(screen.getByRole("button", { name: "DDInter aspirin-warfarin" }));
    expect(screen.queryByRole("link", { name: /view source/i })).not.toBeInTheDocument();
  });
});
