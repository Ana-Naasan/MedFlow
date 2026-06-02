"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import {
  FlaskConical,
  Phone,
  FileText,
  Pill,
  ClipboardList,
  Square,
  CheckSquare as CheckSquareFilled,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useClinicToolsStore } from "@/lib/clinic-tools-store"
import type { ClinicTask, TaskCategory } from "@/lib/mock-data/tasks"

type TaskFilter = "all" | "open" | "done" | "overdue" | "today"

const CATEGORY_ICONS: Record<TaskCategory, React.ComponentType<{ className?: string }>> = {
  lab: FlaskConical,
  referral: FileText,
  callback: Phone,
  admin: ClipboardList,
  rx: Pill,
}

const PRIORITY_STYLES = {
  low: { label: "Low", color: "var(--mf-ink-soft)" },
  medium: { label: "Medium", color: "var(--mf-accent)" },
  high: { label: "High", color: "var(--mf-warm)" },
} as const

const TODAY = "2026-05-31"

export function TasksPageClient() {
  const tasks = useClinicToolsStore((s) => s.tasks)
  const toggleTask = useClinicToolsStore((s) => s.toggleTask)

  const [filter, setFilter] = useState<TaskFilter>("open")

  const counts = useMemo(() => {
    const open = tasks.filter((t) => t.status === "open")
    return {
      open: open.length,
      overdue: open.filter((t) => t.dueDate < TODAY).length,
      today: open.filter((t) => t.dueDate === TODAY).length,
      done: tasks.filter((t) => t.status === "done").length,
    }
  }, [tasks])

  const filtered = useMemo(() => {
    switch (filter) {
      case "open":
        return tasks.filter((t) => t.status === "open")
      case "done":
        return tasks.filter((t) => t.status === "done")
      case "overdue":
        return tasks.filter((t) => t.status === "open" && t.dueDate < TODAY)
      case "today":
        return tasks.filter((t) => t.status === "open" && t.dueDate === TODAY)
      default:
        return tasks
    }
  }, [tasks, filter])

  const filters: { id: TaskFilter; label: string; count?: number }[] = [
    { id: "open", label: "Open", count: counts.open },
    { id: "today", label: "Due today", count: counts.today },
    { id: "overdue", label: "Overdue", count: counts.overdue },
    { id: "done", label: "Completed", count: counts.done },
    { id: "all", label: "All" },
  ]

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <p className="mf-eyebrow mb-1">Clinician</p>
        <h1 className="mf-display text-2xl font-semibold leading-tight">Tasks</h1>
        <p className="mt-1 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          Follow-ups, labs, callbacks, and admin work
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Open", value: counts.open },
          { label: "Due today", value: counts.today },
          { label: "Overdue", value: counts.overdue },
          { label: "Done", value: counts.done },
        ].map(({ label, value }) => (
          <div key={label} className="mf-surface-card p-4">
            <p className="text-xs font-medium" style={{ color: "var(--mf-ink-soft)" }}>
              {label}
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter tasks">
        {filters.map(({ id, label, count }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={filter === id}
            onClick={() => setFilter(id)}
            className={cn(
              "min-h-[44px] rounded-lg border-2 px-4 text-sm font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]",
              filter === id
                ? "border-[var(--mf-ink)] bg-[var(--mf-paper-2)]"
                : "border-transparent text-[var(--mf-ink-soft)] hover:bg-[var(--mf-paper-2)]"
            )}
          >
            {label}
            {count !== undefined && count > 0 && (
              <span className="ml-1.5 tabular-nums opacity-80">({count})</span>
            )}
          </button>
        ))}
      </div>

      <ul className="space-y-2">
        {filtered.length === 0 ? (
          <li className="mf-surface-card p-8 text-center text-sm" style={{ color: "var(--mf-ink-soft)" }}>
            No tasks match this filter.
          </li>
        ) : (
          filtered.map((task) => (
            <TaskRow key={task.id} task={task} onToggle={() => toggleTask(task.id)} />
          ))
        )}
      </ul>
    </div>
  )
}

function TaskRow({ task, onToggle }: { task: ClinicTask; onToggle: () => void }) {
  const Icon = CATEGORY_ICONS[task.category]
  const isDone = task.status === "done"
  const isOverdue = !isDone && task.dueDate < TODAY

  return (
    <li
      className={cn(
        "mf-surface-card flex gap-3 p-4 transition-opacity",
        isDone && "opacity-60"
      )}
    >
      <button
        type="button"
        onClick={onToggle}
        className="mt-0.5 shrink-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]"
        aria-label={isDone ? `Mark "${task.title}" as open` : `Mark "${task.title}" as done`}
      >
        {isDone ? (
          <CheckSquareFilled className="size-5" style={{ color: "var(--mf-accent)" }} />
        ) : (
          <Square className="size-5" style={{ color: "var(--mf-ink-soft)" }} />
        )}
      </button>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className={cn("font-semibold text-sm", isDone && "line-through")}>{task.title}</p>
          <span
            className="shrink-0 text-[10px] font-semibold uppercase tracking-wide"
            style={{ color: PRIORITY_STYLES[task.priority].color }}
          >
            {PRIORITY_STYLES[task.priority].label}
          </span>
        </div>
        {task.description && (
          <p className="mt-1 text-sm leading-snug" style={{ color: "var(--mf-ink-soft)" }}>
            {task.description}
          </p>
        )}
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs" style={{ color: "var(--mf-ink-soft)" }}>
          <span className="inline-flex items-center gap-1 capitalize">
            <Icon className="size-3.5" aria-hidden />
            {task.category}
          </span>
          <span>Assignee: {task.assignee}</span>
          <span className={cn(isOverdue && "font-semibold text-[var(--mf-warm)]")}>
            Due: {task.dueDate}
            {isOverdue && " (overdue)"}
          </span>
          {task.patientId && task.patientName && (
            <Link
              href={`/patients/${task.patientId}/profile`}
              className="font-semibold hover:underline"
              style={{ color: "var(--mf-accent)" }}
            >
              {task.patientName}
            </Link>
          )}
        </div>
      </div>
    </li>
  )
}
