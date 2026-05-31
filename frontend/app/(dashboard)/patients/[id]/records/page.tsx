import { FileText } from "lucide-react";

import { ComingSoon } from "../../../../../components/layout/ComingSoon";

export default function RecordsTab() {
  return (
    <ComingSoon
      icon={FileText}
      title="Records"
      description="Visit timeline and attached documents. Backed by an EHR connector — once the FHIR Encounter / DocumentReference endpoints are surfaced this tab will populate."
      features={["Visit timeline", "SOAP / vitals drawer", "Attached PDF previews"]}
    />
  );
}
