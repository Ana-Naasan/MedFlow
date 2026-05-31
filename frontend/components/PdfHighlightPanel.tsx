"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";

import type { Span } from "../lib/types";
import { PdfHighlight } from "./PdfHighlight";

interface PdfHighlightPanelProps {
  span: Span;
  label: string | null;
  source?: string;
  onClose: () => void;
}

/**
 * Modal wrapper that surfaces the patient-fact PDF highlight when a
 * `resource` citation carries a `source_span`. Mirrors EvidencePanel's
 * portal + backdrop + Escape behaviour so both citation kinds dismiss the
 * same way.
 */
export function PdfHighlightPanel({ span, label, source, onClose }: PdfHighlightPanelProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return createPortal(
    <>
      <div
        className="evidence-panel-backdrop"
        data-testid="pdf-highlight-backdrop"
        aria-hidden="true"
        onClick={onClose}
      />
      <aside
        className="evidence-panel"
        aria-label={label ?? "Patient record source"}
        data-testid="pdf-highlight-panel"
      >
        <header className="evidence-panel-header">
          <h3>{label ?? "Patient record source"}</h3>
          <button type="button" className="button secondary" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="evidence-panel-body">
          <PdfHighlight span={span} source={source} />
        </div>
      </aside>
    </>,
    document.body
  );
}
