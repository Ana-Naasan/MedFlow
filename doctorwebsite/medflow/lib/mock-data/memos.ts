export type MemoPriority = "normal" | "urgent"
export type MemoStatus = "unread" | "read" | "acknowledged"

export interface ClinicMemo {
  id: string
  subject: string
  body: string
  from: string
  to: string
  patientId?: string
  patientName?: string
  priority: MemoPriority
  status: MemoStatus
  createdAt: string
  requiresAck: boolean
}

export const CLINIC_MEMOS: ClinicMemo[] = [
  {
    id: "memo-001",
    subject: "Stat holiday clinic closure",
    body: "The clinic will be closed Monday for the statutory holiday. On-call coverage is through the regional line. Urgent labs will be batched Tuesday morning.",
    from: "Clinic Admin",
    to: "All providers",
    priority: "urgent",
    status: "unread",
    createdAt: "2026-05-30T12:00:00",
    requiresAck: true,
  },
  {
    id: "memo-002",
    subject: "Whitmore - cardiology report filed",
    body: "Dr. Halloway's surveillance note for Harold Whitmore is in eDocuments. Please review before his June 5 follow-up.",
    from: "MOA - Riverside Desk",
    to: "Park, Eleanor",
    patientId: "24884",
    patientName: "Whitmore, Harold",
    priority: "normal",
    status: "unread",
    createdAt: "2026-05-31T08:15:00",
    requiresAck: false,
  },
  {
    id: "memo-003",
    subject: "Chen - home glucose log uploaded",
    body: "Margaret Chen's daughter emailed a 2-week glucose log. PDF saved to chart Files. Fasting values mostly 7-9 mmol/L.",
    from: "MOA - Edmonton North",
    to: "Chen, James",
    patientId: "10231",
    patientName: "Chen, Margaret",
    priority: "normal",
    status: "read",
    createdAt: "2026-05-29T14:20:00",
    requiresAck: false,
  },
  {
    id: "memo-004",
    subject: "Patel - pharmacy clarification",
    body: "Shoppers on Oak Ave needs clarification on sertraline dose change. Patient reachable at (403) 555-0301.",
    from: "Pharmacy Fax",
    to: "Wu, Bella",
    patientId: "33591",
    patientName: "Patel, Raj",
    priority: "urgent",
    status: "read",
    createdAt: "2026-05-31T07:45:00",
    requiresAck: true,
  },
  {
    id: "memo-005",
    subject: "Morrison - INR outside range",
    body: "Today's INR is 4.2 (target 2-3). Patient has not been contacted yet. Please advise dose hold or repeat.",
    from: "LifeLabs Interface",
    to: "Chen, James",
    patientId: "68103",
    patientName: "Morrison, Gerald",
    priority: "urgent",
    status: "acknowledged",
    createdAt: "2026-05-28T11:00:00",
    requiresAck: true,
  },
]
