// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DataGapsBanner } from "../components/DataGapsBanner";

describe("DataGapsBanner", () => {
  it("renders nothing when there are no gaps", () => {
    const { container } = render(<DataGapsBanner gaps={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders the notice + each gap as a list item", () => {
    render(
      <DataGapsBanner
        gaps={[
          "medications not returned by source",
          "Skipped Observation/x: validation failed",
        ]}
      />
    );
    expect(screen.getByTestId("data-gaps-banner")).toBeInTheDocument();
    expect(
      screen.getByText(/some data could not be retrieved/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText("medications not returned by source")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Skipped Observation/x: validation failed")
    ).toBeInTheDocument();
  });

  it("uses a polite live region so screen readers do not interrupt review", () => {
    render(<DataGapsBanner gaps={["Allergies not returned by source"]} />);
    const banner = screen.getByTestId("data-gaps-banner");
    // Non-blocking: status + polite, NOT role="alert".
    expect(banner).toHaveAttribute("role", "status");
    expect(banner).toHaveAttribute("aria-live", "polite");
  });
});
