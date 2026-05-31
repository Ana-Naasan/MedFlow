// All MedFlow domain types — zero `any`

export type Sex = "male" | "female" | "other";

export type AllergySeverity = "mild" | "moderate" | "severe";

export type EncounterType = "office-visit" | "telehealth" | "walk-in" | "emergency" | "specialist";

export type InvestigationType = "lab" | "radiology" | "cardiology" | "requisition" | "referral" | "or" | "misc";

export type InvestigationStatus = "pending" | "in-progress" | "completed" | "cancelled";

export type NoteTag = "clinical" | "admin" | "referral" | "prescription";

export type BillingStatus = "paid" | "pending" | "rejected";

export type FileType = "pdf" | "dicom" | "image" | "document";

export type EDocType = "referral-letter" | "lab-report" | "imaging-report" | "consent-form" | "discharge-summary";

export type EDocStatus = "received" | "sent" | "pending";

export type InvestigationSource = "Lab (LifeLabs)" | "Radiology" | "Cardiology" | "Other";

// ─── Core models ─────────────────────────────────────────────────────────────

export interface Allergy {
  name: string;
  severity: AllergySeverity;
  reaction?: string;
}

export interface Medication {
  name: string;
  dose?: string;
  instructions: string;
  prescribedDate?: string;
}

export interface Problem {
  code: string;
  description: string;
  onsetDate?: string;
  status: "active" | "resolved";
}

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone: string;
}

export interface Patient {
  id: string;
  name: { first: string; last: string };
  dob: string;
  sex: Sex;
  location: string;
  healthNumber: string;
  familyPhysician?: string;
  referringPhysician?: string;
  primaryPhysician: string;
  phone?: string;
  email?: string;
  address?: string;
  allergies: Allergy[];
  medications: Medication[];
  problems: Problem[];
  emergencyContacts: EmergencyContact[];
  immunizationUpToDate: boolean;
}

export interface VitalsSnapshot {
  bp?: string;
  hr?: number;
  temp?: number;
  weight?: number;
  height?: number;
  o2sat?: number;
  recordedAt: string;
}

export interface Encounter {
  id: string;
  patientId: string;
  date: string;
  type: EncounterType;
  physician: string;
  chiefComplaint: string;
  summary: string;
  vitals?: VitalsSnapshot;
  soapNotes?: {
    subjective: string;
    objective: string;
    assessment: string;
    plan: string;
  };
  prescriptions?: string[];
  attachedDocuments?: string[];
}

export interface Investigation {
  id: string;
  patientId: string;
  date: string;
  type: InvestigationType;
  source: InvestigationSource;
  description: string;
  status: InvestigationStatus;
  orderedBy: string;
  referringPhysician?: string;
  notes?: string;
  statusHistory: Array<{
    status: InvestigationStatus;
    date: string;
    updatedBy: string;
  }>;
  attachedFiles?: string[];
}

export interface Note {
  id: string;
  patientId: string;
  date: string;
  author: string;
  title: string;
  content: string;
  tags: NoteTag[];
  lastEditedAt: string;
}

export interface BillingEntry {
  id: string;
  patientId: string;
  date: string;
  serviceCode: string;
  description: string;
  amount: number;
  status: BillingStatus;
}

export interface FileRecord {
  id: string;
  patientId: string;
  name: string;
  type: FileType;
  uploadedAt: string;
  uploadedBy: string;
  sizeKb: number;
  url?: string;
}

export interface EDocument {
  id: string;
  patientId: string;
  date: string;
  docType: EDocType;
  sender: string;
  recipient: string;
  status: EDocStatus;
  subject: string;
  content: string;
  faxNumber?: string;
}

export interface Doctor {
  id: string;
  email: string;
  name: string;
  role: string;
}
