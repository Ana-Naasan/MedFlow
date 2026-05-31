"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { $api } from "../lib/api";
import type { Citation, Span } from "../lib/types";
import { PdfHighlight } from "./PdfHighlight";

interface CitationChipProps {
  citation: Citation;
  patientId: string;
}

export function CitationChip({ citation, patientId }: CitationChipProps) {
  const [open, setOpen] = useState(false);

  const isKnowledge = citation.kind === "evidence";

  const refParts = citation.ref.split("/");
  const resourceType = refParts[0] as string;
  const resourceId = refParts[1] ?? "";

  const resourceQuery = $api.useQuery(
    "get",
    "/patients/{patient_id}/resource/{resource_type}/{resource_id}",
    {
      params: {
        path: { patient_id: patientId, resource_type: resourceType, resource_id: resourceId },
      },
    },
    { enabled: open && citation.kind === "resource" }
  );

  const evidenceQuery = $api.useQuery(
    "get",
    "/evidence/{evidence_id}",
    { params: { path: { evidence_id: citation.ref } } },
    { enabled: open && citation.kind === "evidence" }
  );

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  const activeQuery = citation.kind === "resource" ? resourceQuery : evidenceQuery;
  const responseData = activeQuery.data as Record<string, unknown> | undefined;
  const snippet = responseData?.snippet as string | undefined;
  const source = responseData?.source as string | undefined;
  const responseId = responseData?.id as string | undefined;
  const span = responseData?.span as Span | undefined;
  const refUrl = responseData?.ref_url as string | undefined;
  // Only surface http(s) links — guards against javascript:/data: schemes from the untyped response.
  const sourceUrl = refUrl && /^https?:\/\//i.test(refUrl) ? refUrl : undefined;

  const getPanelBody = () => {
    if (activeQuery.isLoading) {
      return (
        <div className="citation-skeleton" role="status" aria-label="Loading citation">
          <div className="skeleton-line" />
          <div className="skeleton-line skeleton-line-short" />
        </div>
      );
    }
    if (activeQuery.isError) return <p>Failed to load citation.</p>;
    if (!responseData) return null;
    if (span) return <PdfHighlight span={span} source={source} />;
    if (snippet) return <p className="citation-panel-snippet">{snippet}</p>;
    return (
      <p className="citation-panel-snippet">
        {responseId ? `Resource: ${responseId}` : "Source not found."}
      </p>
    );
  };

  return (
    <>
      <button
        type="button"
        className={`chip-interactive ${isKnowledge ? "chip-knowledge" : "chip-resource"}`}
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
      >
        {citation.label ?? citation.ref}
      </button>
      {open &&
        createPortal(
          <>
            <div
              className="modal-backdrop"
              data-testid="modal-backdrop"
              aria-hidden="true"
              onClick={() => setOpen(false)}
            />
            <dialog
              open
              className="citation-panel"
              aria-modal="true"
              aria-label={citation.label ?? citation.ref}
            >
              <p className="citation-panel-source">
                {source ?? citation.label ?? citation.ref}
              </p>
              {getPanelBody()}
              {sourceUrl && (
                <a
                  className="citation-panel-link"
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View source
                  <span aria-hidden="true"> ↗</span>
                </a>
              )}
              <div className="citation-panel-footer">
                <button type="button" className="button secondary" onClick={() => setOpen(false)}>
                  Close
                </button>
              </div>
            </dialog>
          </>,
          document.body
        )}
    </>
  );
}
