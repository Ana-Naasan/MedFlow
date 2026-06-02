import type { BillingEntry } from "@/lib/types";

// Canadian provincial billing codes (Alberta Health)
// A001 — Office visit, minor ailment (< 10 min)
// A003 — Office visit, general assessment
// A007 — Telehealth visit
// A901 — House call
// G003 — Comprehensive visit, complex patient
// G100 — Annual health review
// G372 — Mental health assessment
// G374 — Mental health follow-up
// Q040 — Telephone management
// Z422 — Spirometry interpretation

export const billingEntries: BillingEntry[] = [
  // ─── Margaret Chen (10231) ───────────────────────────────────────────────────
  {
    id: "bill-005",
    patientId: "10231",
    date: "2024-02-08",
    serviceCode: "G003",
    description: "Comprehensive visit — diabetes, HTN, hyperlipidaemia review",
    amount: 92.75,
    status: "paid",
  },
  {
    id: "bill-006",
    patientId: "10231",
    date: "2023-10-12",
    serviceCode: "A003",
    description: "Office visit — 3-month chronic disease follow-up",
    amount: 37.89,
    status: "paid",
  },
  {
    id: "bill-007",
    patientId: "10231",
    date: "2024-05-20",
    serviceCode: "A007",
    description: "Telehealth visit — orthostatic hypotension assessment",
    amount: 31.50,
    status: "pending",
  },
  {
    id: "bill-008",
    patientId: "10231",
    date: "2024-08-15",
    serviceCode: "G100",
    description: "Annual health review — medication review and immunizations",
    amount: 74.50,
    status: "rejected",
  },
  {
    id: "bill-009",
    patientId: "10231",
    date: "2024-08-15",
    serviceCode: "A003",
    description: "Vaccine administration — influenza QIV-HD and Pneumovax 23",
    amount: 27.60,
    status: "pending",
  },

  // ─── Raj Patel (33591) ───────────────────────────────────────────────────────
  {
    id: "bill-010",
    patientId: "33591",
    date: "2023-08-14",
    serviceCode: "G372",
    description: "Mental health assessment — MDD initial evaluation (PHQ-9, safety screen)",
    amount: 61.20,
    status: "paid",
  },
  {
    id: "bill-011",
    patientId: "33591",
    date: "2024-03-05",
    serviceCode: "G374",
    description: "Mental health follow-up — Sertraline review and CBT referral",
    amount: 45.85,
    status: "paid",
  },
  {
    id: "bill-012",
    patientId: "33591",
    date: "2024-06-18",
    serviceCode: "A007",
    description: "Telehealth visit — GERD assessment and Pantoprazole initiation",
    amount: 31.50,
    status: "paid",
  },
  {
    id: "bill-013",
    patientId: "33591",
    date: "2024-09-22",
    serviceCode: "G003",
    description: "Comprehensive visit — annual medication review, MDD and GERD",
    amount: 92.75,
    status: "pending",
  },
  {
    id: "bill-014",
    patientId: "33591",
    date: "2023-09-10",
    serviceCode: "Q040",
    description: "Telephone management — Sertraline side effect query",
    amount: 15.30,
    status: "rejected",
  },

  // ─── Sophie Dubois (57720) ───────────────────────────────────────────────────
  {
    id: "bill-015",
    patientId: "57720",
    date: "2024-04-11",
    serviceCode: "A003",
    description: "Office visit — eczema flare assessment and treatment",
    amount: 37.89,
    status: "paid",
  },
  {
    id: "bill-016",
    patientId: "57720",
    date: "2023-09-06",
    serviceCode: "A003",
    description: "Post-anaphylaxis follow-up office visit",
    amount: 37.89,
    status: "paid",
  },
  {
    id: "bill-017",
    patientId: "57720",
    date: "2024-07-30",
    serviceCode: "G100",
    description: "Annual health review — allergy and eczema management plan",
    amount: 74.50,
    status: "pending",
  },
  {
    id: "bill-018",
    patientId: "57720",
    date: "2023-09-05",
    serviceCode: "G003",
    description: "Comprehensive ER follow-up — anaphylaxis management (ER billed separately)",
    amount: 92.75,
    status: "rejected",
  },

  // ─── Gerald Morrison (68103) ─────────────────────────────────────────────────
  {
    id: "bill-019",
    patientId: "68103",
    date: "2024-01-22",
    serviceCode: "G003",
    description: "Comprehensive visit — HF, AFib, CKD, T2DM quarterly review",
    amount: 92.75,
    status: "paid",
  },
  {
    id: "bill-020",
    patientId: "68103",
    date: "2023-09-18",
    serviceCode: "G003",
    description: "Post-discharge follow-up — acute decompensated heart failure",
    amount: 92.75,
    status: "paid",
  },
  {
    id: "bill-021",
    patientId: "68103",
    date: "2024-04-03",
    serviceCode: "A003",
    description: "Office visit — cardiology recommendations review (SGLT2i initiation)",
    amount: 37.89,
    status: "paid",
  },
  {
    id: "bill-022",
    patientId: "68103",
    date: "2024-07-15",
    serviceCode: "A001",
    description: "Office visit — supratherapeutic INR management",
    amount: 21.45,
    status: "pending",
  },
  {
    id: "bill-023",
    patientId: "68103",
    date: "2024-09-05",
    serviceCode: "A003",
    description: "Office visit — dyspnea assessment, chest X-ray ordered",
    amount: 37.89,
    status: "pending",
  },

  // ─── Harold Whitmore (24884) ─────────────────────────────────────────────────
  {
    id: "bill-hw-001",
    patientId: "24884",
    date: "2010-09-15",
    serviceCode: "G003",
    description: "New patient comprehensive history & physical",
    amount: 92.75,
    status: "paid",
  },
  {
    id: "bill-hw-002",
    patientId: "24884",
    date: "2010-10-13",
    serviceCode: "A003",
    description: "Office visit — 4-week fasting lab review",
    amount: 37.89,
    status: "paid",
  },
  {
    id: "bill-hw-003",
    patientId: "24884",
    date: "2012-03-22",
    serviceCode: "G100",
    description: "Annual health review + smoking cessation counseling",
    amount: 74.50,
    status: "paid",
  },
  {
    id: "bill-hw-004",
    patientId: "24884",
    date: "2014-11-10",
    serviceCode: "G003",
    description: "Comprehensive visit — type 2 diabetes diagnosis",
    amount: 92.75,
    status: "paid",
  },
  {
    id: "bill-hw-005",
    patientId: "24884",
    date: "2022-04-19",
    serviceCode: "G003",
    description: "Comprehensive visit — cardiac workup (echo, Holter)",
    amount: 92.75,
    status: "pending",
  },
  {
    id: "bill-hw-006",
    patientId: "24884",
    date: "2026-03-08",
    serviceCode: "G100",
    description: "Annual health review — glycemic reassessment",
    amount: 74.50,
    status: "pending",
  },
];

export function getBillingByPatientId(patientId: string): BillingEntry[] {
  return billingEntries.filter((b) => b.patientId === patientId);
}

export function getBillingEntryById(id: string): BillingEntry | undefined {
  return billingEntries.find((b) => b.id === id);
}

export function getBillingTotalByPatientId(patientId: string): number {
  return getBillingByPatientId(patientId).reduce((sum, entry) => sum + entry.amount, 0);
}
