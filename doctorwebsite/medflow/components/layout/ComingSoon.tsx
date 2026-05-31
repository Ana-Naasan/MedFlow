import type { LucideIcon } from "lucide-react"

interface ComingSoonProps {
  icon: LucideIcon
  title: string
  description: string
  features: string[]
}

export function ComingSoon({ icon: Icon, title, description, features }: ComingSoonProps) {
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-56px)] px-6">
      <div className="max-w-xl w-full text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[var(--bg-subtle)] mb-6">
          <Icon className="w-8 h-8 text-[var(--accent)]" strokeWidth={1.5} />
        </div>

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--accent)]/10 mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
          <span className="text-xs font-medium text-[var(--accent)] uppercase tracking-wider">Coming Soon</span>
        </div>

        <h1 className="text-3xl font-semibold text-[var(--foreground)] mb-3">
          {title}
        </h1>

        <p className="text-base text-[var(--text-secondary)] mb-8 leading-relaxed">
          {description}
        </p>

        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-6 text-left shadow-[var(--shadow-sm)]">
          <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-4">
            What&apos;s coming
          </p>
          <ul className="space-y-3">
            {features.map((feature, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-[var(--foreground)]">
                <span className="mt-1.5 w-1 h-1 rounded-full bg-[var(--accent)] flex-shrink-0" />
                <span>{feature}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="mt-6 text-xs text-[var(--text-muted)]">
          We&apos;re building this carefully. Check back soon.
        </p>
      </div>
    </div>
  )
}
