"use client"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

/**
 * Maps a source-derived tier string (severity or confidence) to one of the
 * MedFlow token color families. The clinical invariant is that these tiers are
 * source-derived — we render them faithfully as badges and never editorialize.
 *
 * Unknown / unrecognised tiers fall through to a neutral "muted" treatment so a
 * surprise value from the backend never crashes or implies a risk level we
 * cannot justify.
 */
export type TierTone = "success" | "warning" | "danger" | "muted"

function toTone(raw: string): TierTone {
  const v = raw.trim().toLowerCase()
  if (v === "high" || v === "severe" || v === "critical") return "danger"
  if (v === "medium" || v === "moderate" || v === "mid") return "warning"
  if (v === "low" || v === "mild" || v === "minor") return "success"
  return "muted"
}

const TONE_CLASS: Record<TierTone, string> = {
  // token-driven tints — no hardcoded hex; color-mix keeps text legible on paper
  danger:
    "bg-[color-mix(in_oklch,var(--danger)_12%,transparent)] text-[var(--danger)] border-[color-mix(in_oklch,var(--danger)_24%,transparent)]",
  warning:
    "bg-[color-mix(in_oklch,var(--warning)_14%,transparent)] text-[var(--warning)] border-[color-mix(in_oklch,var(--warning)_28%,transparent)]",
  success:
    "bg-[color-mix(in_oklch,var(--success)_12%,transparent)] text-[var(--success)] border-[color-mix(in_oklch,var(--success)_24%,transparent)]",
  muted:
    "bg-muted text-muted-foreground border-border",
}

interface TierBadgeProps {
  /** The tier label rendered verbatim (e.g. "high", "moderate"). */
  value: string
  /** Prefix shown before the tier, e.g. "Confidence". */
  prefix?: string
  className?: string
}

/**
 * A tier badge for severity / confidence. The displayed text is the raw tier
 * value (optionally prefixed); only the COLOR is derived from the tier so the
 * source language is preserved.
 */
export function TierBadge({ value, prefix, className }: TierBadgeProps) {
  const tone = toTone(value)
  return (
    <Badge
      variant="outline"
      className={cn("border", TONE_CLASS[tone], className)}
    >
      {prefix ? `${prefix}: ${value}` : value}
    </Badge>
  )
}
