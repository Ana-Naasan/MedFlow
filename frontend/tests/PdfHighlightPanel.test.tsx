// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PdfHighlightPanel } from "../components/PdfHighlightPanel";
import type { Span } from "../lib/types";

const span: Span = {
  page: 2,
  start: 143,
  end: 183,
  snippet: "Warfarin 5 mg oral Anticoagulant Daily",
};

describe("PdfHighlightPanel", () => {
  it("renders the PdfHighlight with the span snippet", () => {
    render(<PdfHighlightPanel span={span} label="Warfarin (PDF)" onClose={() => {}} />);
    expect(screen.getByTestId("pdf-highlight")).toBeInTheDocument();
    expect(screen.getByText("Warfarin 5 mg oral Anticoagulant Daily")).toBeInTheDocument();
  });

  it("uses the label as the panel aria-label and heading", () => {
    render(<PdfHighlightPanel span={span} label="Warfarin (PDF)" onClose={() => {}} />);
    const panel = screen.getByTestId("pdf-highlight-panel");
    expect(panel).toHaveAttribute("aria-label", "Warfarin (PDF)");
    expect(screen.getByRole("heading", { name: "Warfarin (PDF)" })).toBeInTheDocument();
  });

  it("falls back to a default label when label is null", () => {
    render(<PdfHighlightPanel span={span} label={null} onClose={() => {}} />);
    const panel = screen.getByTestId("pdf-highlight-panel");
    expect(panel).toHaveAttribute("aria-label", "Patient record source");
    expect(
      screen.getByRole("heading", { name: "Patient record source" })
    ).toBeInTheDocument();
  });

  it("forwards the source label to PdfHighlight", () => {
    render(
      <PdfHighlightPanel span={span} label="Warfarin (PDF)" source="Chart PDF" onClose={() => {}} />
    );
    expect(screen.getByText(/PDF · Page 2 · Chart PDF/i)).toBeInTheDocument();
  });

  it("calls onClose when the Close button is clicked", () => {
    const onClose = vi.fn();
    render(<PdfHighlightPanel span={span} label="Warfarin (PDF)" onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the backdrop is clicked", () => {
    const onClose = vi.fn();
    render(<PdfHighlightPanel span={span} label="Warfarin (PDF)" onClose={onClose} />);
    fireEvent.click(screen.getByTestId("pdf-highlight-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape is pressed", () => {
    const onClose = vi.fn();
    render(<PdfHighlightPanel span={span} label="Warfarin (PDF)" onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose for other keys", () => {
    const onClose = vi.fn();
    render(<PdfHighlightPanel span={span} label="Warfarin (PDF)" onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Enter" });
    expect(onClose).not.toHaveBeenCalled();
  });
});
