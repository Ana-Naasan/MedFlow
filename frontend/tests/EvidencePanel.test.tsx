// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/api", () => ({
  $api: { useQuery: vi.fn() },
}));

import { $api } from "../lib/api";
import { EvidencePanel } from "../components/EvidencePanel";

const mockIdle = { data: undefined, isLoading: false, isError: false };
const mockLoading = { data: undefined, isLoading: true, isError: false };
const mockError = { data: undefined, isLoading: false, isError: true };

const mockFullData = {
  data: {
    id: "ddinter-aspirin-warfarin",
    snippet: "Aspirin and warfarin may increase bleeding risk.",
    source: "DDInter",
    ref_url: "https://ddinter.scbdd.com/",
  },
  isLoading: false,
  isError: false,
};

const mockNoUrl = {
  data: {
    id: "ev-no-url",
    snippet: "Some clinical note.",
    source: "openFDA",
  },
  isLoading: false,
  isError: false,
};

describe("EvidencePanel", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked($api.useQuery).mockReturnValue(mockIdle as never);
  });

  // ── Rendering ────────────────────────────────────────────────────────────

  it("renders snippet and source from evidence response", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockFullData as never);
    render(<EvidencePanel evidenceId="ddinter-aspirin-warfarin" label="DDInter" onClose={onClose} />);
    expect(screen.getByText("Aspirin and warfarin may increase bleeding risk.")).toBeInTheDocument();
    // Source name appears in the body (separate from heading)
    expect(screen.getByText("DDInter", { selector: ".evidence-panel-source" })).toBeInTheDocument();
  });

  it("renders external link when ref_url is present", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockFullData as never);
    render(<EvidencePanel evidenceId="ddinter-aspirin-warfarin" label="DDInter" onClose={onClose} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://ddinter.scbdd.com/");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("omits external link when ref_url is absent", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockNoUrl as never);
    render(<EvidencePanel evidenceId="ev-no-url" label="openFDA" onClose={onClose} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("renders error state when fetch fails — shows Source unavailable", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockError as never);
    render(<EvidencePanel evidenceId="ev-001" label="Test" onClose={onClose} />);
    expect(screen.getByText("Source unavailable")).toBeInTheDocument();
  });

  it("renders error state when data is empty — shows Source unavailable", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockIdle as never);
    render(<EvidencePanel evidenceId="ev-001" label="Test" onClose={onClose} />);
    expect(screen.getByText("Source unavailable")).toBeInTheDocument();
  });

  it("renders loading skeleton while fetching", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockLoading as never);
    render(<EvidencePanel evidenceId="ev-001" label="Test" onClose={onClose} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("uses label as panel heading", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockFullData as never);
    render(<EvidencePanel evidenceId="ddinter-aspirin-warfarin" label="DDInter" onClose={onClose} />);
    expect(screen.getByRole("heading", { name: "DDInter" })).toBeInTheDocument();
  });

  it("falls back to evidenceId as heading when label is null", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockFullData as never);
    render(<EvidencePanel evidenceId="ddinter-aspirin-warfarin" label={null} onClose={onClose} />);
    expect(screen.getByRole("heading", { name: "ddinter-aspirin-warfarin" })).toBeInTheDocument();
  });

  // ── Dismiss behaviour ────────────────────────────────────────────────────

  it("close button calls onClose", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockFullData as never);
    render(<EvidencePanel evidenceId="ev-001" label="Test" onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("backdrop click calls onClose", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockFullData as never);
    render(<EvidencePanel evidenceId="ev-001" label="Test" onClose={onClose} />);
    fireEvent.click(screen.getByTestId("evidence-panel-backdrop"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("Escape key calls onClose", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockFullData as never);
    render(<EvidencePanel evidenceId="ev-001" label="Test" onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  // ── API wiring ────────────────────────────────────────────────────────────

  it("calls GET /evidence/{evidence_id} with correct id", () => {
    vi.mocked($api.useQuery).mockReturnValue(mockFullData as never);
    render(<EvidencePanel evidenceId="ddinter-aspirin-warfarin" label="DDInter" onClose={onClose} />);
    const calls = vi.mocked($api.useQuery).mock.calls;
    const call = calls.find((c) => c[1] === "/evidence/{evidence_id}");
    expect(call).toBeDefined();
    expect(
      (call![2] as unknown as { params: { path: { evidence_id: string } } }).params.path.evidence_id
    ).toBe("ddinter-aspirin-warfarin");
  });
});
