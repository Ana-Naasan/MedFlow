import { FileEdit } from "lucide-react";

import { ComingSoon } from "../../../components/layout/ComingSoon";

export default function MemosPage() {
  return (
    <ComingSoon
      icon={FileEdit}
      title="Memos"
      description="Inter-clinician messaging and one-off broadcast notes."
    />
  );
}
