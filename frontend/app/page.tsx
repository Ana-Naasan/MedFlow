import Link from "next/link";
import { Stethoscope, UserRound } from "lucide-react";

/**
 * Role-select splash. Per #(migration-decision) we skip a real /login —
 * clicking a role just lands the user on that role's home. Both still hit the
 * same FastAPI backend with the bearer DEV_TOKEN from
 * NEXT_PUBLIC_API_TOKEN; the role here is purely a UI gate.
 */
export default function HomePage() {
  return (
    <main className="min-h-screen flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-3xl">
        <header className="text-center mb-10">
          <p className="mf-eyebrow mb-3">Umraa demo</p>
          <h1 className="mf-display text-4xl sm:text-5xl font-semibold text-foreground mb-3">
            Welcome
          </h1>
          <p className="text-mf-ink-soft max-w-md mx-auto">
            Choose how you&rsquo;d like to explore the demo. No login &mdash;
            just pick a role.
          </p>
        </header>

        <div className="grid sm:grid-cols-2 gap-4">
          <RoleCard
            href="/dashboard"
            icon={<Stethoscope className="size-6" aria-hidden />}
            eyebrow="For clinicians"
            title="Continue as Doctor"
            body="See the patient directory, drill into a chart, and review the cited decision packet."
            primary
            data-testid="role-doctor"
          />
          <RoleCard
            href="/patient/dashboard"
            icon={<UserRound className="size-6" aria-hidden />}
            eyebrow="For patients"
            title="Continue as Patient"
            body="Walk through intake, care selection, and the booking flow as a member."
            data-testid="role-patient"
          />
        </div>
      </div>
    </main>
  );
}

interface RoleCardProps {
  href: string;
  icon: React.ReactNode;
  eyebrow: string;
  title: string;
  body: string;
  primary?: boolean;
  "data-testid"?: string;
}

function RoleCard({
  href,
  icon,
  eyebrow,
  title,
  body,
  primary,
  ...rest
}: RoleCardProps) {
  return (
    <Link
      href={href}
      data-testid={rest["data-testid"]}
      className={
        "group block rounded-[10px] border-2 border-mf-ink p-6 text-left " +
        "transition-colors focus-visible:outline focus-visible:outline-2 " +
        "focus-visible:outline-offset-2 focus-visible:outline-mf-accent " +
        (primary
          ? "bg-accent text-accent-foreground hover:opacity-95"
          : "bg-card text-foreground hover:bg-mf-paper-2")
      }
    >
      <div
        className={
          "mb-4 inline-flex items-center justify-center w-12 h-12 rounded-lg " +
          (primary ? "bg-white/15" : "bg-accent/10 text-accent")
        }
      >
        {icon}
      </div>
      <p
        className={
          "mf-eyebrow mb-2 " + (primary ? "!text-white/80" : "!text-accent")
        }
      >
        {eyebrow}
      </p>
      <h2
        className={
          "mf-display text-xl font-semibold mb-2 " +
          (primary ? "text-white" : "text-foreground")
        }
      >
        {title}
      </h2>
      <p
        className={
          "text-sm " + (primary ? "text-white/80" : "text-mf-ink-soft")
        }
      >
        {body}
      </p>
    </Link>
  );
}
