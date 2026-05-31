// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Skeleton } from "../components/ui/Skeleton";

describe("Skeleton", () => {
  it("is announced to assistive tech as a status loader", () => {
    render(<Skeleton />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-label", "Loading");
  });

  it("merges custom className", () => {
    render(<Skeleton className="h-12 my-class" />);
    const el = screen.getByRole("status");
    expect(el.className).toMatch(/h-12/);
    expect(el.className).toMatch(/my-class/);
  });

  it("always pulses (used as the universal loading hint)", () => {
    render(<Skeleton />);
    expect(screen.getByRole("status").className).toMatch(/animate-pulse/);
  });
});
