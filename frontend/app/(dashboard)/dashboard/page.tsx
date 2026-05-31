"use client";

import { CalendarDays, ChevronRight, FlaskConical, Users } from "lucide-react";
import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card";
import { Skeleton } from "../../../components/ui/Skeleton";
import { usePatients } from "../../../lib/usePatients";

/**
 * Clinician dashboard home. Stat cards on top (medflow-style), recent-patients
 * card below populated from the LIVE ``/patients`` endpoint — the stat counts
 * for the "Patients Today" tile are derived from the same response so the
 * page is honest about what's actually in the cache.
 */
export default function DashboardPage() {
  const { data, isLoading, isError, error } = usePatients();

  const patientCount = data?.length ?? 0;
  const today = new Date().toLocaleDateString("en-CA", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header className="space-y-1">
        <p className="mf-eyebrow mb-1">Clinical dashboard</p>
        <h1 className="mf-display text-[32px] font-semibold leading-tight text-foreground">
          Good day, Clinician
        </h1>
        <p className="text-sm text-mf-ink-soft">{today}</p>
      </header>

      <section aria-label="Summary statistics" className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Patients in cache"
          value={isLoading ? "…" : String(patientCount)}
          icon={<Users className="size-5" aria-hidden />}
          testId="stat-patients"
        />
        <StatCard
          label="Pending decisions"
          value="—"
          icon={<FlaskConical className="size-5" aria-hidden />}
          testId="stat-pending"
        />
        <StatCard
          label="Scheduled today"
          value="—"
          icon={<CalendarDays className="size-5" aria-hidden />}
          testId="stat-scheduled"
        />
      </section>

      <section aria-label="Recent patients">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>Recently in cache</CardTitle>
              <CardDescription>
                Patients with a cached decision packet on this deployment.
              </CardDescription>
            </div>
            <Link
              href="/directory"
              className="text-sm text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mf-accent"
              data-testid="see-all-patients"
            >
              See all →
            </Link>
          </CardHeader>
          <CardContent>
            {isLoading && (
              <ul className="space-y-2" aria-label="Loading patients">
                <li><Skeleton className="h-10" /></li>
                <li><Skeleton className="h-10" /></li>
                <li><Skeleton className="h-10" /></li>
              </ul>
            )}
            {isError && (
              <p className="text-sm text-destructive" role="alert" data-testid="patients-error">
                Failed to load patients
                {error instanceof Error ? `: ${error.message}` : "."}
              </p>
            )}
            {!isLoading && !isError && data && data.length === 0 && (
              <p className="text-sm text-mf-ink-soft" data-testid="patients-empty">
                No patients in cache yet. Run an intake to populate the directory.
              </p>
            )}
            {!isLoading && !isError && data && data.length > 0 && (
              <ul className="divide-y divide-border" data-testid="patients-list">
                {data.slice(0, 5).map((p) => (
                  <li key={p.id}>
                    <Link
                      href={`/patients/${encodeURIComponent(p.id)}/profile`}
                      className="flex items-center justify-between py-3 transition-colors hover:bg-mf-paper-2 -mx-3 px-3 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mf-accent"
                    >
                      <span className="font-medium text-foreground">{p.id}</span>
                      <ChevronRight className="size-4 text-mf-ink-soft" aria-hidden />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  testId: string;
}

function StatCard({ label, value, icon, testId }: StatCardProps) {
  return (
    <Card data-testid={testId}>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex size-10 items-center justify-center rounded-lg bg-accent-soft text-accent">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="mf-eyebrow !text-[10px]">{label}</p>
          <p className="mf-display text-2xl font-semibold text-foreground">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
