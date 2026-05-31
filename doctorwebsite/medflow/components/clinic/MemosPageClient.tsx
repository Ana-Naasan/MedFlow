"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { AlertCircle, Check, StickyNote, User } from "lucide-react"
import { cn } from "@/lib/utils"
import { useClinicToolsStore } from "@/lib/clinic-tools-store"
import type { ClinicMemo, MemoStatus } from "@/lib/mock-data/memos"

const FILTER_OPTIONS: { id: "all" | MemoStatus; label: string }[] = [
  { id: "all", label: "All" },
  { id: "unread", label: "Unread" },
  { id: "read", label: "Read" },
  { id: "acknowledged", label: "Acknowledged" },
]

function formatWhen(iso: string): string {
  const d = new Date(iso)
  const now = new Date("2026-05-31T10:00:00")
  const diffMs = now.getTime() - d.getTime()
  const hours = Math.floor(diffMs / 3_600_000)
  if (hours < 24) return `${hours}h ago`
  return d.toLocaleDateString("en-CA", { month: "short", day: "numeric" })
}

export function MemosPageClient() {
  const memos = useClinicToolsStore((s) => s.memos)
  const markMemoRead = useClinicToolsStore((s) => s.markMemoRead)
  const acknowledgeMemo = useClinicToolsStore((s) => s.acknowledgeMemo)

  const [filter, setFilter] = useState<"all" | MemoStatus>("all")
  const [selectedId, setSelectedId] = useState<string | null>(memos[0]?.id ?? null)

  const filtered = useMemo(() => {
    if (filter === "all") return memos
    return memos.filter((m) => m.status === filter)
  }, [memos, filter])

  const selected = memos.find((m) => m.id === selectedId) ?? filtered[0]

  const unreadCount = memos.filter((m) => m.status === "unread").length

  function selectMemo(memo: ClinicMemo) {
    setSelectedId(memo.id)
    markMemoRead(memo.id)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mf-eyebrow mb-1">Clinician</p>
          <h1 className="mf-display text-2xl font-semibold leading-tight">Memos</h1>
          <p className="mt-1 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
            Internal messages for your clinic team
            {unreadCount > 0 && (
              <span className="ml-2 font-semibold" style={{ color: "var(--mf-accent)" }}>
                {unreadCount} unread
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter memos">
        {FILTER_OPTIONS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={filter === id}
            onClick={() => setFilter(id)}
            className={cn(
              "min-h-[44px] rounded-lg border-2 px-4 text-sm font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]",
              filter === id
                ? "border-[var(--mf-ink)] bg-[var(--mf-paper-2)] text-[var(--mf-ink)]"
                : "border-transparent text-[var(--mf-ink-soft)] hover:bg-[var(--mf-paper-2)]"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,340px)_1fr]">
        <ul className="mf-surface-card divide-y overflow-hidden" style={{ borderColor: "var(--mf-paper-2)" }}>
          {filtered.length === 0 ? (
            <li className="p-6 text-center text-sm" style={{ color: "var(--mf-ink-soft)" }}>
              No memos in this view.
            </li>
          ) : (
            filtered.map((memo) => (
              <li key={memo.id}>
                <button
                  type="button"
                  onClick={() => selectMemo(memo)}
                  className={cn(
                    "flex w-full gap-3 px-4 py-3 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--mf-accent)]",
                    selected?.id === memo.id && "bg-[var(--mf-accent-soft)]/50",
                    memo.status === "unread" && selected?.id !== memo.id && "bg-[var(--mf-paper-2)]/60"
                  )}
                >
                  <StickyNote
                    className="mt-0.5 size-4 shrink-0"
                    style={{ color: "var(--mf-accent)" }}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-start justify-between gap-2">
                      <span
                        className={cn(
                          "truncate text-sm",
                          memo.status === "unread" ? "font-semibold" : "font-medium"
                        )}
                      >
                        {memo.subject}
                      </span>
                      {memo.priority === "urgent" && (
                        <AlertCircle className="size-4 shrink-0 text-[var(--mf-warm)]" aria-label="Urgent" />
                      )}
                    </span>
                    <span className="mt-0.5 block truncate text-xs" style={{ color: "var(--mf-ink-soft)" }}>
                      {memo.from} | {formatWhen(memo.createdAt)}
                    </span>
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>

        {selected ? (
          <article className="mf-surface-card flex flex-col p-6">
            <header className="border-b pb-4" style={{ borderColor: "var(--mf-paper-2)" }}>
              <h2 className="mf-display text-xl font-semibold">{selected.subject}</h2>
              <p className="mt-2 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
                <span className="font-medium text-[var(--mf-ink)]">From:</span> {selected.from}
                {" | "}
                <span className="font-medium text-[var(--mf-ink)]">To:</span> {selected.to}
              </p>
              <p className="mt-1 text-xs" style={{ color: "var(--mf-ink-soft)" }}>
                {new Date(selected.createdAt).toLocaleString("en-CA", {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
            </header>

            <div className="flex-1 py-4 text-sm leading-relaxed whitespace-pre-wrap">{selected.body}</div>

            {selected.patientId && selected.patientName && (
              <Link
                href={`/patients/${selected.patientId}/profile`}
                className="mb-4 inline-flex items-center gap-2 text-sm font-semibold hover:underline"
                style={{ color: "var(--mf-accent)" }}
              >
                <User className="size-4" aria-hidden />
                Open chart: {selected.patientName}
              </Link>
            )}

            <footer className="flex flex-wrap gap-2 border-t pt-4" style={{ borderColor: "var(--mf-paper-2)" }}>
              {selected.requiresAck && selected.status !== "acknowledged" && (
                <button
                  type="button"
                  onClick={() => acknowledgeMemo(selected.id)}
                  className="mf-btn-primary text-sm"
                >
                  <Check className="size-4" aria-hidden />
                  Acknowledge
                </button>
              )}
              {selected.status === "acknowledged" && (
                <span
                  className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium"
                  style={{ background: "var(--mf-accent-soft)", color: "var(--mf-accent)" }}
                >
                  <Check className="size-4" aria-hidden />
                  Acknowledged
                </span>
              )}
            </footer>
          </article>
        ) : (
          <div
            className="mf-surface-card flex items-center justify-center p-12 text-sm"
            style={{ color: "var(--mf-ink-soft)" }}
          >
            Select a memo to read
          </div>
        )}
      </div>
    </div>
  )
}
