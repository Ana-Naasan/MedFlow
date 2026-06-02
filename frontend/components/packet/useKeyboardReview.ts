"use client"

import { useCallback, useEffect, useRef } from "react"

import type { Hypothesis } from "@/lib/api/types"

/**
 * Keyboard-review wiring for the AI Review differential.
 *
 * Bindings (mirrors the reference app's review ergonomics):
 *   j / ArrowDown  → move focus to the next hypothesis card
 *   k / ArrowUp    → move focus to the previous hypothesis card
 *   c              → confirm (acknowledge) the focused hypothesis
 *   d / x          → dismiss the focused hypothesis
 *   Enter          → open the focused hypothesis's primary citation in the drawer
 *   Escape         → close the evidence drawer
 *
 * Cards are addressed in the DOM via `[data-hypothesis-id]` (the stable
 * attribute HypothesisCard already renders), so focus tracking survives
 * re-renders and refetch-driven removals. Keys are ignored while an editable
 * element (input/textarea/select/contenteditable) holds focus so typing is
 * never hijacked.
 */
export interface KeyboardReviewHandlers {
  /** Confirm/acknowledge the hypothesis with this id. */
  onConfirm: (id: string) => void
  /** Dismiss the hypothesis with this id. */
  onDismiss: (id: string) => void
  /** Open the primary (first) citation of the hypothesis with this id. */
  onOpenPrimaryCitation: (hypothesis: Hypothesis) => void
  /** Close the evidence drawer. */
  onCloseDrawer: () => void
  /** Whether the drawer is currently open (Esc/Enter behavior differs). */
  drawerOpen: boolean
}

function isEditableTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false
  const tag = el.tagName
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true
  if (el.isContentEditable) return true
  return false
}

/**
 * True when focus rests on an in-card interactive control (an action button or
 * anything inside the citations/actions slots). Review shortcuts (c/d/j/k/Enter)
 * are suppressed there so the control keeps its native keyboard semantics —
 * mirroring the existing Enter guard.
 */
function isInCardControl(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false
  if (el.tagName === "BUTTON") return true
  return el.closest(
    '[data-slot="hypothesis-actions"],[data-slot="hypothesis-citations"]',
  ) != null
}

export function useKeyboardReview(
  hypotheses: Hypothesis[],
  handlers: KeyboardReviewHandlers
) {
  // Mirror inputs into a ref so the listener (attached once) always reads the
  // latest list + callbacks without re-subscribing on every render. The write
  // happens after commit (in an effect) rather than during render so React's
  // concurrent rendering never observes a torn ref.
  const stateRef = useRef({ hypotheses, handlers })
  useEffect(() => {
    stateRef.current = { hypotheses, handlers }
  })

  /** Index of the currently focused card, or -1 if focus is elsewhere. */
  const focusedIndex = useCallback((ids: string[]): number => {
    const active = document.activeElement
    if (!(active instanceof HTMLElement)) return -1
    const card = active.closest<HTMLElement>("[data-hypothesis-id]")
    if (!card) return -1
    const id = card.getAttribute("data-hypothesis-id")
    return id ? ids.indexOf(id) : -1
  }, [])

  const focusCard = useCallback((id: string) => {
    const el = document.querySelector<HTMLElement>(
      `[data-hypothesis-id="${CSS.escape(id)}"]`
    )
    el?.focus()
  }, [])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const { hypotheses: hyps, handlers: h } = stateRef.current

      // Escape always closes the drawer, even mid-typing — but if the drawer
      // is open the Sheet handles its own Escape, so we no-op here to avoid
      // double-handling.
      if (e.key === "Escape") {
        if (!h.drawerOpen) return
        return // Sheet's onOpenChange handles the close.
      }

      // Never hijack typing.
      if (isEditableTarget(e.target)) return
      // While the drawer is open, let it own the keyboard (focus is trapped
      // inside the Sheet); review keys resume once it closes.
      if (h.drawerOpen) return

      const ids = hyps.map((x) => x.id)
      if (ids.length === 0) return
      const idx = focusedIndex(ids)

      // When an in-card control (action button, citation/action slot) holds
      // focus, let it own the keyboard — review shortcuts (c/d/j/k) and Enter
      // must not fire over native control activation.
      if (isInCardControl(e.target)) return

      switch (e.key) {
        case "j":
        case "ArrowDown": {
          e.preventDefault()
          const next = idx < 0 ? 0 : Math.min(idx + 1, ids.length - 1)
          focusCard(ids[next])
          break
        }
        case "k":
        case "ArrowUp": {
          e.preventDefault()
          const prev = idx < 0 ? 0 : Math.max(idx - 1, 0)
          focusCard(ids[prev])
          break
        }
        case "c": {
          if (idx < 0) return
          e.preventDefault()
          h.onConfirm(ids[idx])
          break
        }
        case "d":
        case "x": {
          if (idx < 0) return
          e.preventDefault()
          h.onDismiss(ids[idx])
          break
        }
        case "Enter": {
          if (idx < 0) return
          // Enter on a card opens its primary citation; let buttons keep their
          // native Enter activation (handled before this via isEditableTarget?
          // No — buttons aren't editable, so guard explicitly).
          if (
            e.target instanceof HTMLElement &&
            e.target.tagName === "BUTTON"
          ) {
            return
          }
          e.preventDefault()
          h.onOpenPrimaryCitation(hyps[idx])
          break
        }
        default:
          break
      }
    }

    document.addEventListener("keydown", onKeyDown)
    return () => document.removeEventListener("keydown", onKeyDown)
  }, [focusCard, focusedIndex])
}
