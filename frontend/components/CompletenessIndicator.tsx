import type { CategoryCompleteness } from "../lib/types";

interface CompletenessIndicatorProps {
  completeness: CategoryCompleteness[];
}

export function CompletenessIndicator({ completeness }: CompletenessIndicatorProps) {
  if (completeness.length === 0) return null;

  return (
    <aside className="completeness-panel panel card stack" aria-label="Data completeness">
      <h3 className="completeness-title">Data Completeness</h3>
      <ul className="completeness-list">
        {completeness.map((item) => (
          <li
            key={item.category}
            className={`completeness-item ${item.documented ? "completeness-documented" : "completeness-gap"}`}
          >
            <span className="completeness-icon" aria-hidden="true">
              {item.documented ? "✓" : "!"}
            </span>
            <span className="completeness-category">{item.category}</span>
            {!item.documented && item.gap_note && (
              <span className="completeness-gap-note">{item.gap_note}</span>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
}
