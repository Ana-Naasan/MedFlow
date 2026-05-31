// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "../app/page";

describe("HomePage — role-select splash", () => {
  it("renders the doctor role card pointing at /dashboard", () => {
    render(<HomePage />);
    const doctor = screen.getByTestId("role-doctor");
    expect(doctor).toHaveAttribute("href", "/dashboard");
    expect(doctor).toHaveTextContent(/continue as doctor/i);
  });

  it("renders the patient role card pointing at /patient/dashboard", () => {
    render(<HomePage />);
    const patient = screen.getByTestId("role-patient");
    expect(patient).toHaveAttribute("href", "/patient/dashboard");
    expect(patient).toHaveTextContent(/continue as patient/i);
  });

  it("does NOT render a /login link (we explicitly skipped real auth)", () => {
    render(<HomePage />);
    expect(
      screen.queryByRole("link", { name: /sign in|log in/i }),
    ).not.toBeInTheDocument();
  });
});
