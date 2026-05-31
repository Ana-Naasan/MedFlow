import { CheckSquare } from "lucide-react";

import { ComingSoon } from "../../../components/layout/ComingSoon";

export default function TasksPage() {
  return (
    <ComingSoon
      icon={CheckSquare}
      title="Tasks"
      description="Action items derived from confirmed decision-packet hypotheses. Will populate as the confirm/dismiss flow persists state to the backend."
    />
  );
}
