interface DataGapsBannerProps {
  gaps: string[];
}

export function DataGapsBanner({ gaps }: DataGapsBannerProps) {
  if (gaps.length === 0) return null;
  return (
    <aside
      className="data-gaps-banner"
      role="status"
      aria-live="polite"
      aria-label="Data gaps"
      data-testid="data-gaps-banner"
    >
      <p className="data-gaps-banner-title">
        Some data could not be retrieved from this source.
      </p>
      <ul className="data-gaps-banner-list">
        {gaps.map((gap) => (
          <li key={gap}>{gap}</li>
        ))}
      </ul>
    </aside>
  );
}
