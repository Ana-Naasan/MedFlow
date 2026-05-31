import { FileSignature } from "lucide-react";

import { ComingSoon } from "../../../../../components/layout/ComingSoon";

export default function EDocumentsTab() {
  return (
    <ComingSoon
      icon={FileSignature}
      title="eDocuments"
      description="CareConnect / Compose sub-tabs and the document viewer modal. Waiting on a documents API surface."
    />
  );
}
