"use client"

interface PacketSummaryProps {
  /** The packet's `summary_markdown`. Rendered as lightweight prose. */
  markdown: string
}

/**
 * Renders the packet summary as a styled prose block. We deliberately avoid a
 * heavy markdown dependency: the backend summary is short narrative text, so we
 * split on blank lines into paragraphs and on newlines into soft line breaks,
 * stripping the most common leading markers (#, -, *) for a clean read.
 */
export function PacketSummary({ markdown }: PacketSummaryProps) {
  const text = markdown?.trim() ?? ""
  if (!text) return null

  const blocks = text.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean)

  return (
    <section
      aria-label="Summary"
      className="rounded-lg border border-border bg-bg-surface p-5"
    >
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Summary
      </h3>
      <div className="mt-3 space-y-3">
        {blocks.map((block, i) => {
          const lines = block.split("\n").map(stripMarker)
          return (
            <p
              key={i}
              className="text-sm leading-relaxed text-[var(--text-secondary)]"
            >
              {lines.map((line, j) => (
                <span key={j}>
                  {line}
                  {j < lines.length - 1 && <br />}
                </span>
              ))}
            </p>
          )
        })}
      </div>
    </section>
  )
}

/** Strip a single leading markdown bullet / heading marker for plain display. */
function stripMarker(line: string): string {
  return line.replace(/^\s*(?:#{1,6}\s+|[-*+]\s+)/, "")
}
