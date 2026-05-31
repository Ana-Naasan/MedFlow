"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";

import { $api } from "../lib/api";

interface EvidencePanelProps {
  evidenceId: string;
  label: string | null;
  onClose: () => void;
}

export function EvidencePanel({ evidenceId, label, onClose }: EvidencePanelProps) {
  const query = $api.useQuery("get", "/evidence/{evidence_id}", {
    params: { path: { evidence_id: evidenceId } },
  });

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const data = query.data as Record<string, unknown> | undefined;
  const snippet = data?.snippet as string | undefined;
  const source = data?.source as string | undefined;
  const refUrl = data?.ref_url as string | undefined;

  const renderBody = () => {
    if (query.isLoading) {
      return (
        <div className="citation-skeleton" role="status" aria-label="Loading evidence">
          <div className="skeleton-line" />
          <div className="skeleton-line skeleton-line-short" />
        </div>
      );
    }
    if (query.isError || !data) {
      return <p className="evidence-panel-error">Source unavailable</p>;
    }
    return (
      <>
        {source && <p className="evidence-panel-source">{source}</p>}
        {snippet && <p className="evidence-panel-snippet">{snippet}</p>}
        {refUrl && (
          <a
            href={refUrl}
            className="evidence-panel-source-link"
            target="_blank"
            rel="noopener noreferrer"
          >
            View source ↗
          </a>
        )}
      </>
    );
  };

  return createPortal(
    <>
      <div
        className="evidence-panel-backdrop"
        data-testid="evidence-panel-backdrop"
        aria-hidden="true"
        onClick={onClose}
      />
      <aside
        className="evidence-panel"
        aria-label={label ?? evidenceId}
        data-testid="evidence-panel"
      >
        <header className="evidence-panel-header">
          <h3>{label ?? evidenceId}</h3>
          <button type="button" className="button secondary" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="evidence-panel-body">{renderBody()}</div>
      </aside>
    </>,
    document.body
  );
}
