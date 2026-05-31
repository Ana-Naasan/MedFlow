import { FlaskConical } from "lucide-react";

import { ComingSoon } from "../../../../../components/layout/ComingSoon";

export default function InvestigationsTab() {
  return (
    <ComingSoon
      icon={FlaskConical}
      title="Investigations"
      description="Lab requisitions, referrals, OR notes. Will pull from a FHIR DiagnosticReport / ServiceRequest endpoint when one is wired up."
    />
  );
}
