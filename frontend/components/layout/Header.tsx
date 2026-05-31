/**
 * Page header above the dashboard main content. Holds the page title
 * (passed in) and a slot for right-aligned actions. Minimal vs medflow's
 * Header because we don't yet ship the global PatientSearch modal.
 */
interface HeaderProps {
  title?: string;
  eyebrow?: string;
  rightSlot?: React.ReactNode;
}

export function Header({ title, eyebrow, rightSlot }: HeaderProps) {
  if (!title && !eyebrow && !rightSlot) return null;
  return (
    <div className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-mf-paper px-4 sm:px-6">
      <div className="min-w-0">
        {eyebrow && <p className="mf-eyebrow !text-[10px]">{eyebrow}</p>}
        {title && (
          <h2 className="mf-display text-lg font-semibold leading-tight text-foreground truncate">
            {title}
          </h2>
        )}
      </div>
      {rightSlot && <div className="ml-4 flex items-center gap-2">{rightSlot}</div>}
    </div>
  );
}
