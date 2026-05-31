// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../components/PacketView", () => ({
  PacketView: vi.fn(({ patientId }: { patientId: string }) => (
    <div data-testid="packet-view">Legacy packet for {patientId}</div>
  )),
}));

import LegacyPacketPage from "../app/(provider)/packet/page";
import { PacketView } from "../components/PacketView";

describe("Legacy /packet route", () => {
  it("mounts PacketView with the historical pat-001 id (back-compat)", () => {
    render(<LegacyPacketPage />);
    expect(screen.getByTestId("packet-view")).toHaveTextContent(
      "Legacy packet for pat-001",
    );
    expect(PacketView).toHaveBeenCalledWith(
      { patientId: "pat-001" },
      expect.anything(),
    );
  });
});
