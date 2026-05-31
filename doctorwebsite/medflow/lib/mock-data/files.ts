import type { FileRecord } from "@/lib/types";
import { whitmoreFiles } from "./whitmore-records";

export const fileRecords: FileRecord[] = [
  // ─── Margaret Chen (10231) ───────────────────────────────────────────────────
  {
    id: "file-005",
    patientId: "10231",
    name: "10231_HbA1c_lipid_CMP_2024-02-10.pdf",
    type: "pdf",
    uploadedAt: "2024-02-10T09:00:00",
    uploadedBy: "LifeLabs System",
    sizeKb: 264,
  },
  {
    id: "file-006",
    patientId: "10231",
    name: "10231_HbA1c_CMP_2023-10-14.pdf",
    type: "pdf",
    uploadedAt: "2023-10-14T10:15:00",
    uploadedBy: "LifeLabs System",
    sizeKb: 231,
  },
  {
    id: "file-007",
    patientId: "10231",
    name: "10231_ophthalmology_referral_letter_2024-08-16.pdf",
    type: "pdf",
    uploadedAt: "2024-08-16T09:30:00",
    uploadedBy: "Admin Staff",
    sizeKb: 112,
  },
  {
    id: "file-008",
    patientId: "10231",
    name: "10231_fundus_photo_right_eye_2022-06-12.dicom",
    type: "dicom",
    uploadedAt: "2022-06-12T15:00:00",
    uploadedBy: "Ophthalmology Clinic",
    sizeKb: 4820,
  },

  // ─── Raj Patel (33591) ───────────────────────────────────────────────────────
  {
    id: "file-009",
    patientId: "33591",
    name: "33591_baseline_labs_TSH_CBC_CMP_2023-08-16.pdf",
    type: "pdf",
    uploadedAt: "2023-08-16T11:00:00",
    uploadedBy: "LifeLabs System",
    sizeKb: 298,
  },
  {
    id: "file-010",
    patientId: "33591",
    name: "33591_PHQ9_score_history_chart.pdf",
    type: "pdf",
    uploadedAt: "2024-09-22T14:30:00",
    uploadedBy: "Wu, Bella",
    sizeKb: 76,
  },
  {
    id: "file-011",
    patientId: "33591",
    name: "33591_psychology_CBT_intake_form_2024-05-01.pdf",
    type: "pdf",
    uploadedAt: "2024-05-01T10:00:00",
    uploadedBy: "Dr. T. Larsson",
    sizeKb: 183,
  },
  {
    id: "file-012",
    patientId: "33591",
    name: "33591_GI_referral_2024-06-18.pdf",
    type: "pdf",
    uploadedAt: "2024-06-18T15:30:00",
    uploadedBy: "Wu, Bella",
    sizeKb: 95,
  },

  // ─── Sophie Dubois (57720) ───────────────────────────────────────────────────
  {
    id: "file-013",
    patientId: "57720",
    name: "57720_tryptase_IgE_CBC_2023-09-07.pdf",
    type: "pdf",
    uploadedAt: "2023-09-07T08:30:00",
    uploadedBy: "LifeLabs System",
    sizeKb: 201,
  },
  {
    id: "file-014",
    patientId: "57720",
    name: "57720_eczema_photo_forearms_2024-04-11.jpg",
    type: "image",
    uploadedAt: "2024-04-11T11:20:00",
    uploadedBy: "Wu, Bella",
    sizeKb: 1450,
  },
  {
    id: "file-015",
    patientId: "57720",
    name: "57720_allergy_action_plan_2023-09-06.pdf",
    type: "pdf",
    uploadedAt: "2023-09-06T09:45:00",
    uploadedBy: "Wu, Bella",
    sizeKb: 165,
  },
  {
    id: "file-016",
    patientId: "57720",
    name: "57720_EpiPen_prescription_2024-07-30.pdf",
    type: "pdf",
    uploadedAt: "2024-07-30T11:15:00",
    uploadedBy: "Wu, Bella",
    sizeKb: 88,
  },

  // ─── Gerald Morrison (68103) ─────────────────────────────────────────────────
  {
    id: "file-017",
    patientId: "68103",
    name: "68103_INR_CMP_BNP_HbA1c_2024-01-24.pdf",
    type: "pdf",
    uploadedAt: "2024-01-24T10:00:00",
    uploadedBy: "LifeLabs System",
    sizeKb: 312,
  },
  {
    id: "file-018",
    patientId: "68103",
    name: "68103_echo_LVEF_2024-04-03.dicom",
    type: "dicom",
    uploadedAt: "2024-04-03T16:00:00",
    uploadedBy: "Cardiology — Dr. R. Kapoor",
    sizeKb: 8740,
  },
  {
    id: "file-019",
    patientId: "68103",
    name: "68103_holter_48h_report_2024-04-03.pdf",
    type: "pdf",
    uploadedAt: "2024-04-03T16:30:00",
    uploadedBy: "Cardiology — Dr. R. Kapoor",
    sizeKb: 427,
  },
  {
    id: "file-020",
    patientId: "68103",
    name: "68103_CXR_2024-09-06.dicom",
    type: "dicom",
    uploadedAt: "2024-09-06T13:00:00",
    uploadedBy: "Radiology Dept",
    sizeKb: 5120,
  },
  {
    id: "file-021",
    patientId: "68103",
    name: "68103_discharge_summary_2023-09-04.pdf",
    type: "pdf",
    uploadedAt: "2023-09-04T17:00:00",
    uploadedBy: "Royal Alexandra Hospital",
    sizeKb: 560,
  },
];

export function getFilesByPatientId(patientId: string): FileRecord[] {
  return [...fileRecords, ...whitmoreFiles].filter((f) => f.patientId === patientId);
}

export function getFileById(id: string): FileRecord | undefined {
  return [...fileRecords, ...whitmoreFiles].find((f) => f.id === id);
}
