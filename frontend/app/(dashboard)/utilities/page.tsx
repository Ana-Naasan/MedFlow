import { Settings } from "lucide-react";

import { ComingSoon } from "../../../components/layout/ComingSoon";

export default function UtilitiesPage() {
  return (
    <ComingSoon
      icon={Settings}
      title="Utilities"
      description="Configuration surface — environment + connector status, log rotation, cache TTL knobs."
    />
  );
}
