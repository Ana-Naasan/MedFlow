import { create } from "zustand"
import { persist } from "zustand/middleware"
import { CLINICIAN_NOTIFICATIONS } from "@/lib/mock-data/notifications"
import type {
  CareCategoryId,
  ConfirmedBooking,
  PatientOutcome,
} from "@/lib/patient-flow/types"

interface MedFlowStore {
  searchOpen: boolean
  setSearchOpen: (open: boolean) => void
  readNotificationIds: string[]
  markNotificationRead: (id: string) => void
  markAllNotificationsRead: () => void
  recentPatientIds: string[]
  addRecentPatient: (id: string) => void
  patientCareCategory: CareCategoryId | null
  patientIntakeAnswers: Record<string, string[]>
  patientOutcome: PatientOutcome | null
  patientBooking: ConfirmedBooking | null
  setPatientCareCategory: (category: CareCategoryId) => void
  setPatientIntakeAnswer: (questionId: string, answers: string[]) => void
  setPatientOutcome: (outcome: PatientOutcome) => void
  setPatientBooking: (booking: ConfirmedBooking) => void
  clearPatientFlow: () => void
}

export const useMedFlowStore = create<MedFlowStore>()(
  persist(
    (set) => ({
      searchOpen: false,
      setSearchOpen: (open) => set({ searchOpen: open }),
      readNotificationIds: [],
      markNotificationRead: (id) =>
        set((state) => ({
          readNotificationIds: state.readNotificationIds.includes(id)
            ? state.readNotificationIds
            : [...state.readNotificationIds, id],
        })),
      markAllNotificationsRead: () =>
        set({
          readNotificationIds: CLINICIAN_NOTIFICATIONS.map((n) => n.id),
        }),
      recentPatientIds: ["24884", "10231", "68103"],
      addRecentPatient: (id) =>
        set((state) => ({
          recentPatientIds: [
            id,
            ...state.recentPatientIds.filter((r) => r !== id),
          ].slice(0, 5),
        })),
      patientCareCategory: null,
      patientIntakeAnswers: {},
      patientOutcome: null,
      patientBooking: null,
      setPatientCareCategory: (category) =>
        set({
          patientCareCategory: category,
          patientIntakeAnswers: {},
          patientOutcome: null,
          patientBooking: null,
        }),
      setPatientIntakeAnswer: (questionId, answers) =>
        set((state) => ({
          patientIntakeAnswers: {
            ...state.patientIntakeAnswers,
            [questionId]: answers,
          },
        })),
      setPatientOutcome: (outcome) => set({ patientOutcome: outcome }),
      setPatientBooking: (booking) => set({ patientBooking: booking }),
      clearPatientFlow: () =>
        set({
          patientCareCategory: null,
          patientIntakeAnswers: {},
          patientOutcome: null,
          patientBooking: null,
        }),
    }),
    {
      name: "medflow-patient-flow",
      partialize: (state) => ({
        patientCareCategory: state.patientCareCategory,
        patientIntakeAnswers: state.patientIntakeAnswers,
        patientOutcome: state.patientOutcome,
        patientBooking: state.patientBooking,
        readNotificationIds: state.readNotificationIds,
      }),
    }
  )
)
