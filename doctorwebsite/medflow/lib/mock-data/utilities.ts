export type UtilityCategory = "integrations" | "workflow" | "templates" | "account"

export interface UtilityToggle {
  id: string
  category: UtilityCategory
  label: string
  description: string
  enabled: boolean
}

export interface UtilityLink {
  id: string
  label: string
  description: string
  href: string
}

export const UTILITY_TOGGLES: UtilityToggle[] = [
  {
    id: "int-lifelabs",
    category: "integrations",
    label: "LifeLabs results feed",
    description: "Auto-import lab PDFs and flag abnormal results.",
    enabled: true,
  },
  {
    id: "int-efax",
    category: "integrations",
    label: "eFax send/receive",
    description: "Outbound referrals and inbound consult letters.",
    enabled: true,
  },
  {
    id: "int-pharmacy",
    category: "integrations",
    label: "Pharmacy renewal queue",
    description: "Surface renewal requests as tasks.",
    enabled: true,
  },
  {
    id: "int-careconnect",
    category: "integrations",
    label: "CareConnect messaging",
    description: "Provincial HIE lookup (demo mode).",
    enabled: false,
  },
  {
    id: "wf-auto-tasks",
    category: "workflow",
    label: "Auto-create tasks from labs",
    description: "Open a task when critical labs are received.",
    enabled: true,
  },
  {
    id: "wf-memo-notify",
    category: "workflow",
    label: "Memo desktop notifications",
    description: "Show header badge for unread urgent memos.",
    enabled: true,
  },
  {
    id: "wf-duplicate-chart",
    category: "workflow",
    label: "Warn on duplicate patient charts",
    description: "Alert when PHN matches an existing record.",
    enabled: true,
  },
  {
    id: "tpl-smart-phrases",
    category: "templates",
    label: "Smart phrases in notes",
    description: "Expand shortcuts like .htn and .dm2 in encounter notes.",
    enabled: true,
  },
  {
    id: "tpl-referral",
    category: "templates",
    label: "Default referral letter template",
    description: "Pre-fill sender block and closing for eDocuments.",
    enabled: true,
  },
]

export const UTILITY_LINKS: UtilityLink[] = [
  {
    id: "link-directory",
    label: "Export patient directory",
    description: "Download CSV of active panel (demo).",
    href: "/directory",
  },
  {
    id: "link-scheduler",
    label: "Print week schedule",
    description: "Open scheduler for print-friendly view.",
    href: "/scheduler",
  },
  {
    id: "link-billing",
    label: "Fee schedule reference",
    description: "Alberta billing codes quick reference.",
    href: "/utilities#billing-codes",
  },
]

export const BILLING_CODE_REFERENCE = [
  { code: "A001", description: "Office visit - minor ailment", amount: 21.45 },
  { code: "A003", description: "Office visit - general assessment", amount: 37.89 },
  { code: "A007", description: "Telehealth visit", amount: 31.5 },
  { code: "G100", description: "Annual health review", amount: 74.5 },
  { code: "G372", description: "Mental health assessment", amount: 92.0 },
  { code: "Q040", description: "Telephone management", amount: 18.25 },
] as const

export const CLINIC_STAFF = [
  { name: "Dr. Bella Wu", role: "Physician", email: "dr.wu@umraa.ca" },
  { name: "Dr. James Chen", role: "Physician", email: "dr.chen@umraa.ca" },
  { name: "Dr. Eleanor Park", role: "Physician", email: "dr.park@umraa.ca" },
  { name: "MOA - Front Desk", role: "Medical office assistant", email: "frontdesk@umraa.ca" },
  { name: "Clinic Admin", role: "Administrator", email: "admin@umraa.ca" },
] as const
