// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CompletenessIndicator } from "../components/CompletenessIndicator";
import type { CategoryCompleteness } from "../lib/types";

const mixedCompleteness: CategoryCompleteness[] = [
  { category: "Medications", documented: true, gap_note: null },
  { category: "Conditions", documented: true, gap_note: null },
  {
    category: "Labs",
    documented: false,
    gap_note: "Renal function labs not available — order BMP/CMP",
  },
  {
    category: "Allergies",
    documented: false,
    gap_note: "Allergy history not provided — verify with patient",
  },
];

const allDocumented: CategoryCompleteness[] = [
  { category: "Patient", documented: true, gap_note: null },
  { category: "Medications", documented: true, gap_note: null },
];

describe("CompletenessIndicator", () => {
  it("renders nothing when completeness list is empty", () => {
    const { container } = render(<CompletenessIndicator completeness={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders all category names", () => {
    render(<CompletenessIndicator completeness={mixedCompleteness} />);
    expect(screen.getByText("Medications")).toBeInTheDocument();
    expect(screen.getByText("Conditions")).toBeInTheDocument();
    expect(screen.getByText("Labs")).toBeInTheDocument();
    expect(screen.getByText("Allergies")).toBeInTheDocument();
  });

  it("shows checkmark icon for documented categories", () => {
    render(<CompletenessIndicator completeness={allDocumented} />);
    const icons = screen.getAllByText("✓");
    expect(icons).toHaveLength(2);
  });

  it("shows warning icon for gap categories", () => {
    render(<CompletenessIndicator completeness={mixedCompleteness} />);
    const icons = screen.getAllByText("!");
    expect(icons).toHaveLength(2);
  });

  it("shows gap notes for undocumented categories", () => {
    render(<CompletenessIndicator completeness={mixedCompleteness} />);
    expect(
      screen.getByText("Renal function labs not available — order BMP/CMP")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Allergy history not provided — verify with patient")
    ).toBeInTheDocument();
  });

  it("does not show gap notes for documented categories", () => {
    render(<CompletenessIndicator completeness={mixedCompleteness} />);
    const medicationsItem = screen.getByText("Medications").closest("li");
    expect(medicationsItem?.querySelector(".completeness-gap-note")).toBeNull();
  });

  it("renders the Data Completeness heading", () => {
    render(<CompletenessIndicator completeness={mixedCompleteness} />);
    expect(screen.getByText("Data Completeness")).toBeInTheDocument();
  });

  it("has an accessible aside label", () => {
    render(<CompletenessIndicator completeness={mixedCompleteness} />);
    expect(screen.getByRole("complementary", { name: "Data completeness" })).toBeInTheDocument();
  });

  it("does not show gap note when gap_note is null for undocumented category", () => {
    const noNoteGap: CategoryCompleteness[] = [
      { category: "Procedures", documented: false, gap_note: null },
    ];
    render(<CompletenessIndicator completeness={noNoteGap} />);
    const item = screen.getByText("Procedures").closest("li");
    expect(item?.querySelector(".completeness-gap-note")).toBeNull();
  });
});
