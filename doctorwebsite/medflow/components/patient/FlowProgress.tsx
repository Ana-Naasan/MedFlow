interface FlowProgressProps {
  current: number
  total: number
  label?: string
}

export function FlowProgress({ current, total, label }: FlowProgressProps) {
  const pct = Math.round((current / total) * 100)
  return (
    <div className="w-full space-y-2" role="progressbar" aria-valuenow={current} aria-valuemin={1} aria-valuemax={total} aria-label={label ?? `Step ${current} of ${total}`}>
      <div className="flex justify-between text-xs font-medium" style={{ color: "var(--mf-ink-soft)" }}>
        <span>{label ?? `Step ${current} of ${total}`}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full" style={{ background: "var(--mf-paper-2)" }}>
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, background: "var(--mf-accent)" }}
        />
      </div>
    </div>
  )
}
