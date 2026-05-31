// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { FlaskConical } from "lucide-react";
import { describe, expect, it } from "vitest";

import { ComingSoon } from "../components/layout/ComingSoon";

describe("ComingSoon", () => {
  it("renders the title + description", () => {
    render(
      <ComingSoon
        icon={FlaskConical}
        title="Investigations"
        description="Lab requisitions, referrals, OR notes."
      />,
    );
    expect(screen.getByTestId("coming-soon")).toBeInTheDocument();
    expect(screen.getByText("Investigations")).toBeInTheDocument();
    expect(
      screen.getByText("Lab requisitions, referrals, OR notes."),
    ).toBeInTheDocument();
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });

  it("renders an optional feature list", () => {
    render(
      <ComingSoon
        icon={FlaskConical}
        title="X"
        description="y"
        features={["alpha", "beta"]}
      />,
    );
    expect(screen.getByText(/alpha/)).toBeInTheDocument();
    expect(screen.getByText(/beta/)).toBeInTheDocument();
  });

  it("omits the feature list when none are passed", () => {
    render(<ComingSoon icon={FlaskConical} title="X" description="y" />);
    expect(screen.queryByText(/alpha/)).not.toBeInTheDocument();
  });
});
