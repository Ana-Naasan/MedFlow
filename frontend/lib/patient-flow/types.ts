export type CareCategoryId =
  | "mental-health"
  | "primary-care"
  | "wellness"
  | "work-life"

export type IntakeQuestionType = "chips" | "yes-no" | "text"

export interface IntakeQuestion {
  id: string
  prompt: string
  type: IntakeQuestionType
  options?: readonly string[]
}

export type PatientOutcome = "low-acuity" | "standard"

export type AppointmentModality = "video" | "phone" | "in-person"

export interface TimeSlot {
  id: string
  start: string
  end: string
  modality: AppointmentModality
}

export interface CareProvider {
  id: string
  name: string
  credential: string
  bio: string
  languages: readonly ("EN" | "FR")[]
  modalities: readonly AppointmentModality[]
  slots: TimeSlot[]
}

export interface ConfirmedBooking {
  providerId: string
  slotId: string
  careCategory: CareCategoryId
}
