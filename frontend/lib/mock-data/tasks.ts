export type TaskPriority = "low" | "medium" | "high"
export type TaskStatus = "open" | "done"
export type TaskCategory = "lab" | "referral" | "callback" | "admin" | "rx"

export interface ClinicTask {
  id: string
  title: string
  description?: string
  patientId?: string
  patientName?: string
  assignee: string
  dueDate: string
  priority: TaskPriority
  status: TaskStatus
  category: TaskCategory
}

export const CLINIC_TASKS: ClinicTask[] = [
  {
    id: "task-001",
    title: "Review Whitmore annual labs",
    description: "HbA1c and renal panel resulted Mar 10. Sign off or message patient.",
    patientId: "24884",
    patientName: "Whitmore, Harold",
    assignee: "Wu, Bella",
    dueDate: "2026-05-31",
    priority: "high",
    status: "open",
    category: "lab",
  },
  {
    id: "task-002",
    title: "Sign cardiology surveillance note",
    description: "Pending signature for Whitmore, Harold - forwarded from MOA.",
    patientId: "24884",
    patientName: "Whitmore, Harold",
    assignee: "Wu, Bella",
    dueDate: "2026-05-31",
    priority: "medium",
    status: "open",
    category: "referral",
  },
  {
    id: "task-003",
    title: "Callback - Patel GERD symptoms",
    description: "Patient left voicemail; reports heartburn despite pantoprazole.",
    patientId: "33591",
    patientName: "Patel, Raj",
    assignee: "Wu, Bella",
    dueDate: "2026-05-31",
    priority: "high",
    status: "open",
    category: "callback",
  },
  {
    id: "task-004",
    title: "Chen - renew metformin",
    description: "Pharmacy renewal request; last visit Feb 2026.",
    patientId: "10231",
    patientName: "Chen, Margaret",
    assignee: "Chen, James",
    dueDate: "2026-06-02",
    priority: "medium",
    status: "open",
    category: "rx",
  },
  {
    id: "task-005",
    title: "Morrison - warfarin dose adjustment",
    description: "Follow up INR 4.2; document plan in chart.",
    patientId: "68103",
    patientName: "Morrison, Gerald",
    assignee: "Chen, James",
    dueDate: "2026-05-30",
    priority: "high",
    status: "open",
    category: "lab",
  },
  {
    id: "task-006",
    title: "Dubois EpiPen renewal",
    description: "Expiry June 2026; fax to Shoppers Sherwood Park.",
    patientId: "57720",
    patientName: "Dubois, Sophie",
    assignee: "Wu, Bella",
    dueDate: "2026-06-05",
    priority: "low",
    status: "open",
    category: "rx",
  },
  {
    id: "task-007",
    title: "Quarterly panel audit",
    description: "Admin: verify incomplete panels for May billing.",
    assignee: "Clinic Admin",
    dueDate: "2026-06-10",
    priority: "low",
    status: "done",
    category: "admin",
  },
  {
    id: "task-008",
    title: "File Dubois allergy action plan",
    description: "Updated school form received; scan to Files.",
    patientId: "57720",
    patientName: "Dubois, Sophie",
    assignee: "MOA - Front Desk",
    dueDate: "2026-05-28",
    priority: "medium",
    status: "done",
    category: "admin",
  },
]
