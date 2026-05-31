export type NotificationType =
  | "lab"
  | "edocument"
  | "appointment"
  | "task"
  | "memo"

export interface ClinicianNotification {
  id: string
  type: NotificationType
  title: string
  message: string
  href: string
  createdAt: string
}

export const CLINICIAN_NOTIFICATIONS: ClinicianNotification[] = [
  {
    id: "notif-001",
    type: "lab",
    title: "Lab results ready",
    message: "CBC results for Chen, Margaret are ready for review.",
    href: "/patients/10231/investigations",
    createdAt: "2026-05-31T08:42:00",
  },
  {
    id: "notif-002",
    type: "edocument",
    title: "Incoming referral",
    message: "New eDocument from Dr. Larsson for Patel, Raj.",
    href: "/patients/33591/edocuments",
    createdAt: "2026-05-31T07:15:00",
  },
  {
    id: "notif-003",
    type: "appointment",
    title: "Appointment in 30 minutes",
    message: "Office visit with Whitmore, Harold at 9:00 AM.",
    href: "/scheduler",
    createdAt: "2026-05-31T09:00:00",
  },
  {
    id: "notif-004",
    type: "task",
    title: "Task due today",
    message: "Annual labs for Whitmore, Harold are ready for review.",
    href: "/patients/24884/investigations",
    createdAt: "2026-05-30T16:20:00",
  },
  {
    id: "notif-005",
    type: "memo",
    title: "Staff memo",
    message: "Clinic closed Monday for statutory holiday.",
    href: "/memos",
    createdAt: "2026-05-30T12:00:00",
  },
]
