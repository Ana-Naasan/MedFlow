// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PdfHighlight } from "../components/PdfHighlight";
import type { Span } from "../lib/types";

const span: Span = {
  page: 2,
  start: 143,
  end: 183,
  snippet: "Warfarin 5 mg oral Anticoagulant Daily",
};

describe("PdfHighlight", () => {
  it("renders the snippet text inside a mark element", () => {
    render(<PdfHighlight span={span} />);
    const mark = screen.getByText("Warfarin 5 mg oral Anticoagulant Daily");
    expect(mark.tagName).toBe("MARK");
  });

  it("shows the page number", () => {
    render(<PdfHighlight span={span} />);
    expect(screen.getByText(/PDF · Page 2/i)).toBeInTheDocument();
  });

  it("shows source label when provided", () => {
    render(<PdfHighlight span={span} source="openFDA" />);
    expect(screen.getByText(/PDF · Page 2 · openFDA/i)).toBeInTheDocument();
  });

  it("omits source segment when source is undefined", () => {
    render(<PdfHighlight span={span} />);
    const meta = screen.getByText(/PDF · Page/i);
    // "PDF · Page 2" only — no trailing " · <source>"
    expect(meta.textContent).toBe("PDF · Page 2");
  });

  it("renders the container with the pdf-highlight test id", () => {
    render(<PdfHighlight span={span} />);
    expect(screen.getByTestId("pdf-highlight")).toBeInTheDocument();
  });

  it("renders a blockquote wrapping the mark", () => {
    const { container } = render(<PdfHighlight span={span} />);
    const blockquote = container.querySelector("blockquote");
    expect(blockquote).not.toBeNull();
    expect(blockquote?.querySelector("mark")).not.toBeNull();
  });

  it("handles page 1 correctly", () => {
    render(<PdfHighlight span={{ ...span, page: 1 }} />);
    expect(screen.getByText(/PDF · Page 1/i)).toBeInTheDocument();
  });
});
