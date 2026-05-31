import { PatientHeader } from "../../../../components/layout/PatientHeader";
import { PatientTabs } from "../../../../components/layout/PatientTabs";

interface PatientLayoutProps {
  children: React.ReactNode;
  params: { id: string };
}

/**
 * Wraps every per-patient route with the sticky header + tabs strip.
 * medflow's equivalent uses async params (Next 16); we're on Next 14 so
 * params is sync. The patient existence check is skipped here — each tab
 * surfaces its own data-load error UI via usePacket / usePatients.
 */
export default function PatientLayout({
  children,
  params,
}: PatientLayoutProps) {
  const patientId = decodeURIComponent(params.id);
  return (
    <div className="flex h-full flex-col">
      <div className="sticky top-0 z-20 bg-mf-paper">
        <PatientHeader patientId={patientId} />
        <PatientTabs patientId={patientId} />
      </div>
      <div className="flex-1 overflow-auto px-6 py-6">{children}</div>
    </div>
  );
}
