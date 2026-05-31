"use client";

import { useParams } from "next/navigation";

import { PacketView } from "../../../../../components/PacketView";

/**
 * Packet tab within the patient detail nav. Renders the same UI as the
 * legacy /packet route but parameterized by the URL patient id, so the
 * Doctor flow can drill from /directory → /patients/[id]/packet.
 */
export default function PatientPacketTab() {
  const params = useParams<{ id: string }>();
  return <PacketView patientId={decodeURIComponent(params.id)} />;
}
