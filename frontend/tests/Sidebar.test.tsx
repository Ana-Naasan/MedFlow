// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

import { usePathname } from "next/navigation";

import { Sidebar } from "../components/layout/Sidebar";

describe("Sidebar", () => {
  it("renders the six clinician nav items", () => {
    vi.mocked(usePathname).mockReturnValue("/dashboard");
    render(<Sidebar />);
    for (const label of [
      "Records",
      "Directory",
      "Scheduler",
      "Memos",
      "Tasks",
      "Utilities",
    ]) {
      expect(
        screen.getByRole("link", { name: new RegExp(label, "i") }),
      ).toBeInTheDocument();
    }
  });

  it("marks the active link with aria-current=page on exact match", () => {
    vi.mocked(usePathname).mockReturnValue("/directory");
    render(<Sidebar />);
    const directory = screen.getByTestId("nav-directory");
    expect(directory).toHaveAttribute("aria-current", "page");
  });

  it("marks the active link on a child route match", () => {
    vi.mocked(usePathname).mockReturnValue("/dashboard/something-extra");
    render(<Sidebar />);
    expect(screen.getByTestId("nav-records")).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("does NOT mark inactive links with aria-current", () => {
    vi.mocked(usePathname).mockReturnValue("/dashboard");
    render(<Sidebar />);
    expect(screen.getByTestId("nav-directory")).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("the sign-out link points back to the role-select home", () => {
    vi.mocked(usePathname).mockReturnValue("/dashboard");
    render(<Sidebar />);
    expect(screen.getByTestId("sign-out")).toHaveAttribute("href", "/");
  });

  it("the home link target is /dashboard", () => {
    vi.mocked(usePathname).mockReturnValue("/dashboard");
    render(<Sidebar />);
    expect(screen.getByRole("link", { name: /umraa home/i })).toHaveAttribute(
      "href",
      "/dashboard",
    );
  });
});
