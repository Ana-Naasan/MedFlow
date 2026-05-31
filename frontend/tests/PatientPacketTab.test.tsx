// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));

vi.mock("../components/PacketView", () => ({
  PacketView: vi.fn(({ patientId }: { patientId: string }) => (
    <div data-testid="packet-view">Packet for {patientId}</div>
  )),
}));

import PatientPacketTab from "../app/(dashboard)/patients/[id]/packet/page";
import { useParams } from "next/navigation";
import { PacketView } from "../components/PacketView";

describe("PatientPacketTab", () => {
  beforeEach(() => {
    // Clear call history but KEEP the mock implementations defined above
    // (resetAllMocks would wipe vi.fn impls including PacketView's render).
    vi.mocked(PacketView).mockClear();
  });

  it("mounts PacketView with the URL patient id", () => {
    vi.mocked(useParams).mockReturnValue({ id: "DEMO-001" });
    render(<PatientPacketTab />);
    expect(screen.getByTestId("packet-view")).toHaveTextContent("Packet for DEMO-001");
    expect(PacketView).toHaveBeenCalledWith({ patientId: "DEMO-001" }, expect.anything());
  });

  it("decodes URL-encoded patient ids", () => {
    vi.mocked(useParams).mockReturnValue({ id: "pat%2D001" });
    render(<PatientPacketTab />);
    expect(PacketView).toHaveBeenLastCalledWith(
      { patientId: "pat-001" },
      expect.anything(),
    );
  });
});
