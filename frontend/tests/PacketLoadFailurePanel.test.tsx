// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PacketLoadFailurePanel } from "../components/PacketLoadFailurePanel";

describe("PacketLoadFailurePanel — hint copy by status", () => {
  it("401 hints at the dev-token mismatch (the #90 dominant cause)", () => {
    render(
      <PacketLoadFailurePanel
        diag={{
          status: 401,
          body: { detail: "Missing bearer token" },
          url: "http://localhost:8000/patients/pat-001/packet",
          elapsedMs: 18,
        }}
      />,
    );
    expect(screen.getByText(/NEXT_PUBLIC_API_TOKEN/)).toBeInTheDocument();
    expect(screen.getByText(/DEV_TOKEN/)).toBeInTheDocument();
    expect(screen.getByTestId("packet-failure-status")).toHaveTextContent("401");
  });

  it("403 routes to the same auth-family hint", () => {
    render(
      <PacketLoadFailurePanel
        diag={{ status: 403, body: null, url: "x", elapsedMs: 1 }}
      />,
    );
    expect(screen.getByText(/unauthorized/i)).toBeInTheDocument();
  });

  it("404 points at the patient id OR base-URL routing", () => {
    render(
      <PacketLoadFailurePanel
        diag={{ status: 404, body: null, url: "x", elapsedMs: 1 }}
      />,
    );
    expect(screen.getByText(/NEXT_PUBLIC_API_BASE_URL|patient id/i)).toBeInTheDocument();
  });

  it("5xx points at backend logs", () => {
    render(
      <PacketLoadFailurePanel
        diag={{ status: 503, body: null, url: "x", elapsedMs: 1 }}
      />,
    );
    expect(screen.getByText(/backend logs/i)).toBeInTheDocument();
  });

  it("undefined status (no response) blames unreachability / CORS / base URL", () => {
    render(
      <PacketLoadFailurePanel
        diag={{ status: undefined, body: null, url: "", elapsedMs: 30000 }}
      />,
    );
    // The hint text is a single <p> that names all three likely causes; the
    // status field separately renders "— (no response)" so we can't rely on
    // `getByText(/no response/)` (it would match both).
    expect(
      screen.getByText(/unreachable.*CORS|CORS.*unreachable/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("packet-failure-status")).toHaveTextContent(
      /no response/i,
    );
  });
});

describe("PacketLoadFailurePanel — body rendering", () => {
  it("stringifies object bodies as JSON", () => {
    render(
      <PacketLoadFailurePanel
        diag={{
          status: 422,
          body: { detail: [{ msg: "field required" }] },
          url: "x",
          elapsedMs: 1,
        }}
      />,
    );
    const body = screen.getByTestId("packet-failure-body");
    expect(body.textContent).toMatch(/field required/);
  });

  it("renders string bodies verbatim", () => {
    render(
      <PacketLoadFailurePanel
        diag={{ status: 500, body: "Internal Server Error", url: "x", elapsedMs: 1 }}
      />,
    );
    expect(screen.getByTestId("packet-failure-body")).toHaveTextContent(
      "Internal Server Error",
    );
  });

  it("omits the body section when body is null", () => {
    render(
      <PacketLoadFailurePanel
        diag={{ status: 401, body: null, url: "x", elapsedMs: 1 }}
      />,
    );
    expect(screen.queryByTestId("packet-failure-body")).not.toBeInTheDocument();
  });

  it("truncates very long bodies so a giant stacktrace doesn't blow up the page", () => {
    const huge = "x".repeat(2000);
    render(
      <PacketLoadFailurePanel
        diag={{ status: 500, body: huge, url: "x", elapsedMs: 1 }}
      />,
    );
    const text = screen.getByTestId("packet-failure-body").textContent ?? "";
    expect(text.length).toBeLessThan(huge.length);
    expect(text).toContain("(truncated)");
  });
});

describe("PacketLoadFailurePanel — accessibility", () => {
  it("is announced as an alert", () => {
    render(
      <PacketLoadFailurePanel
        diag={{ status: 401, body: null, url: "x", elapsedMs: 1 }}
      />,
    );
    const panel = screen.getByTestId("packet-load-failure");
    expect(panel).toHaveAttribute("role", "alert");
    expect(panel).toHaveAttribute("aria-label", "Packet load failure");
  });
});
