import { PacketView } from "../../../components/PacketView";

// Legacy entrypoint — kept for backwards compatibility. The same component
// also mounts at /patients/[id]/packet for the patient-detail tab nav (the
// medflow IA). Hard-coded to "pat-001" to match the historical behaviour.
export default function ProviderPacketPage() {
  return <PacketView patientId="pat-001" />;
}
