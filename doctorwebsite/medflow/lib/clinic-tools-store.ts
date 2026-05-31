import { create } from "zustand"
import { persist } from "zustand/middleware"
import { CLINIC_MEMOS, type ClinicMemo, type MemoStatus } from "@/lib/mock-data/memos"
import { CLINIC_TASKS, type ClinicTask, type TaskStatus } from "@/lib/mock-data/tasks"
import { UTILITY_TOGGLES } from "@/lib/mock-data/utilities"

interface ClinicToolsStore {
  memos: ClinicMemo[]
  tasks: ClinicTask[]
  utilityEnabled: Record<string, boolean>
  setMemoStatus: (id: string, status: MemoStatus) => void
  markMemoRead: (id: string) => void
  acknowledgeMemo: (id: string) => void
  setTaskStatus: (id: string, status: TaskStatus) => void
  toggleTask: (id: string) => void
  setUtilityEnabled: (id: string, enabled: boolean) => void
  resetClinicTools: () => void
}

function seedUtilityMap(): Record<string, boolean> {
  return Object.fromEntries(UTILITY_TOGGLES.map((t) => [t.id, t.enabled]))
}

export const useClinicToolsStore = create<ClinicToolsStore>()(
  persist(
    (set) => ({
      memos: CLINIC_MEMOS,
      tasks: CLINIC_TASKS,
      utilityEnabled: seedUtilityMap(),
      setMemoStatus: (id, status) =>
        set((state) => ({
          memos: state.memos.map((m) => (m.id === id ? { ...m, status } : m)),
        })),
      markMemoRead: (id) =>
        set((state) => ({
          memos: state.memos.map((m) =>
            m.id === id && m.status === "unread" ? { ...m, status: "read" } : m
          ),
        })),
      acknowledgeMemo: (id) =>
        set((state) => ({
          memos: state.memos.map((m) =>
            m.id === id ? { ...m, status: "acknowledged" } : m
          ),
        })),
      setTaskStatus: (id, status) =>
        set((state) => ({
          tasks: state.tasks.map((t) => (t.id === id ? { ...t, status } : t)),
        })),
      toggleTask: (id) =>
        set((state) => ({
          tasks: state.tasks.map((t) =>
            t.id === id
              ? { ...t, status: t.status === "open" ? "done" : "open" }
              : t
          ),
        })),
      setUtilityEnabled: (id, enabled) =>
        set((state) => ({
          utilityEnabled: { ...state.utilityEnabled, [id]: enabled },
        })),
      resetClinicTools: () =>
        set({
          memos: CLINIC_MEMOS,
          tasks: CLINIC_TASKS,
          utilityEnabled: seedUtilityMap(),
        }),
    }),
    {
      name: "medflow-clinic-tools",
      partialize: (state) => ({
        memos: state.memos,
        tasks: state.tasks,
        utilityEnabled: state.utilityEnabled,
      }),
    }
  )
)
