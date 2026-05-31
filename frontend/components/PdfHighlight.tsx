import type { Span } from "../lib/types";

interface PdfHighlightProps {
  span: Span;
  source?: string;
}

export function PdfHighlight({ span, source }: PdfHighlightProps) {
  return (
    <div className="pdf-highlight" data-testid="pdf-highlight">
      <p className="pdf-highlight-meta">
        PDF · Page {span.page}
        {source && ` · ${source}`}
      </p>
      <blockquote className="pdf-highlight-quote">
        <mark className="pdf-highlight-mark">{span.snippet}</mark>
      </blockquote>
    </div>
  );
}
