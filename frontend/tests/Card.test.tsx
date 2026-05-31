// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../components/ui/Card";

describe("Card parts", () => {
  it("renders Card with children", () => {
    render(<Card data-testid="card">hello</Card>);
    expect(screen.getByTestId("card")).toHaveTextContent("hello");
  });

  it("forwards classNames to Card", () => {
    render(<Card className="custom" data-testid="card" />);
    expect(screen.getByTestId("card").className).toMatch(/custom/);
  });

  it("renders CardTitle as an h3", () => {
    render(<CardTitle>The title</CardTitle>);
    const heading = screen.getByRole("heading", { name: "The title", level: 3 });
    expect(heading).toBeInTheDocument();
  });

  it("renders CardDescription as a paragraph", () => {
    render(<CardDescription>helper</CardDescription>);
    expect(screen.getByText("helper").tagName).toBe("P");
  });

  it("renders CardHeader / CardContent / CardFooter", () => {
    render(
      <Card>
        <CardHeader data-testid="head">H</CardHeader>
        <CardContent data-testid="body">B</CardContent>
        <CardFooter data-testid="foot">F</CardFooter>
      </Card>,
    );
    expect(screen.getByTestId("head")).toHaveTextContent("H");
    expect(screen.getByTestId("body")).toHaveTextContent("B");
    expect(screen.getByTestId("foot")).toHaveTextContent("F");
  });
});
