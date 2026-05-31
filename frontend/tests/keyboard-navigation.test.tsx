// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SuggestionCard } from "../components/SuggestionCard";
import type { Hypothesis } from "../lib/types";

vi.mock("../components/CitationChip", () => ({
  CitationChip: ({ citation }: { citation: { label: string | null; ref: string } }) => (
    <span>{citation.label ?? citation.ref}</span>
  ),
}));

const hyp: Hypothesis = {
  id: "hyp-kb-001",
  title: "Warfarin bleeding risk",
  why: "INR is supratherapeutic with concurrent aspirin.",
  severity: "high",
  confidence: "high",
  citations: [{ kind: "resource", ref: "Patient/p1", label: "Patient" }],
};

describe("SuggestionCard — keyboard accessibility", () => {
  it("renders Approve and Dismiss buttons when callbacks are provided", () => {
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dismiss/i })).toBeInTheDocument();
  });

  it("does not render action buttons when no callbacks are provided", () => {
    render(<SuggestionCard hypothesis={hyp} patientId="p1" />);
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dismiss/i })).not.toBeInTheDocument();
  });

  it("Approve button is focusable via keyboard Tab", () => {
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    const approveBtn = screen.getByRole("button", { name: /approve/i });
    approveBtn.focus();
    expect(document.activeElement).toBe(approveBtn);
  });

  it("Dismiss button is focusable via keyboard Tab", () => {
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    const dismissBtn = screen.getByRole("button", { name: /dismiss/i });
    dismissBtn.focus();
    expect(document.activeElement).toBe(dismissBtn);
  });

  // Approve/Dismiss are native <button> elements, which the browser activates
  // on Enter/Space and dispatches a click for. jsdom does NOT synthesize that
  // click from a keydown, so we assert the native-button guarantee explicitly
  // (tagName + no role override) and that activation invokes the handler —
  // rather than masking the assertion with a manual fireEvent.click after keyDown.
  it("Approve is a native button (Enter/Space-activatable) and calls onConfirm when activated", () => {
    const onConfirm = vi.fn();
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={onConfirm}
        onDismiss={vi.fn()}
      />
    );
    const approveBtn = screen.getByRole("button", { name: /approve/i });
    expect(approveBtn.tagName).toBe("BUTTON");
    expect(approveBtn.getAttribute("role")).toBeNull();
    fireEvent.click(approveBtn);
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("Dismiss is a native button (Enter/Space-activatable) and calls onDismiss when activated", () => {
    const onDismiss = vi.fn();
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={onDismiss}
      />
    );
    const dismissBtn = screen.getByRole("button", { name: /dismiss/i });
    expect(dismissBtn.tagName).toBe("BUTTON");
    expect(dismissBtn.getAttribute("role")).toBeNull();
    fireEvent.click(dismissBtn);
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("buttons are disabled while acting", () => {
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
        isActing
      />
    );
    expect(screen.getByRole("button", { name: /approve/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /dismiss/i })).toBeDisabled();
  });

  it("shows ✓ Approved status and hides buttons after confirm", () => {
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
        status="confirmed"
      />
    );
    expect(screen.getByText(/✓ Approved/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dismiss/i })).not.toBeInTheDocument();
  });

  it("shows ✗ Dismissed status and hides buttons after dismiss", () => {
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
        status="dismissed"
      />
    );
    expect(screen.getByText(/✗ Dismissed/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });

  it("approveRef callback receives the Approve button element", () => {
    let capturedEl: HTMLButtonElement | null = null;
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
        approveRef={(el) => { capturedEl = el; }}
      />
    );
    const approveBtn = screen.getByRole("button", { name: /approve/i });
    expect(capturedEl).toBe(approveBtn);
  });

  it("Approve button has a descriptive aria-label", () => {
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    expect(
      screen.getByRole("button", { name: `Approve: ${hyp.title}` })
    ).toBeInTheDocument();
  });

  it("Dismiss button has a descriptive aria-label", () => {
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    expect(
      screen.getByRole("button", { name: `Dismiss: ${hyp.title}` })
    ).toBeInTheDocument();
  });

  it("Tab order: Approve comes before Dismiss in DOM order", () => {
    render(
      <SuggestionCard
        hypothesis={hyp}
        patientId="p1"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    const buttons = screen.getAllByRole("button");
    const approveIdx = buttons.findIndex((b) => /approve/i.test(b.getAttribute("aria-label") ?? ""));
    const dismissIdx = buttons.findIndex((b) => /dismiss/i.test(b.getAttribute("aria-label") ?? ""));
    expect(approveIdx).toBeLessThan(dismissIdx);
  });
});
