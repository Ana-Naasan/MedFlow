import { CalendarDays } from "lucide-react";

import { ComingSoon } from "../../../components/layout/ComingSoon";

export default function SchedulerPage() {
  return (
    <ComingSoon
      icon={CalendarDays}
      title="Scheduler"
      description="Day-view appointment calendar with drag-to-reschedule."
    />
  );
}
