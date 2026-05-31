// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "../components/ui/Button";

describe("Button", () => {
  it("renders its label", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
  });

  it("forwards click events", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Approve</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("defaults type to button (not submit) so forms don't submit accidentally", () => {
    render(<Button>X</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "button");
  });

  it("honours an explicit type=submit", () => {
    render(<Button type="submit">Submit</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "submit");
  });

  it("applies the primary variant by default", () => {
    render(<Button>X</Button>);
    expect(screen.getByRole("button").className).toMatch(/bg-primary/);
  });

  it("applies the secondary variant when requested", () => {
    render(<Button variant="secondary">X</Button>);
    expect(screen.getByRole("button").className).toMatch(/bg-card/);
  });

  it("applies the destructive variant when requested", () => {
    render(<Button variant="destructive">Delete</Button>);
    expect(screen.getByRole("button").className).toMatch(/bg-destructive/);
  });

  it("supports a custom className that wins where Tailwind classes conflict", () => {
    render(<Button className="bg-red-500">X</Button>);
    // tailwind-merge keeps the override:
    expect(screen.getByRole("button").className).toMatch(/bg-red-500/);
  });

  it("is disabled when disabled prop is set", () => {
    render(<Button disabled>X</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
