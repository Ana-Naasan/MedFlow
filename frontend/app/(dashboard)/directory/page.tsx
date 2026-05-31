"use client";

import Link from "next/link";

import { Skeleton } from "../../../components/ui/Skeleton";
import { usePatients } from "../../../lib/usePatients";

/**
 * Clinician patient directory. Live ``/patients`` list rendered as a table —
 * the medflow wireframe shows DOB / location / physician columns that we
 * don't carry in the backend response yet (patient list returns only
 * ``{id}``), so the table is intentionally one-column today. As the API
 * grows to surface display name / DOB, this is the page that consumes it.
 */
export default function DirectoryPage() {
  const { data, isLoading, isError, error } = usePatients();

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <p className="mf-eyebrow mb-1">Clinician</p>
        <h1 className="mf-display text-2xl font-semibold leading-tight text-foreground">
          Patient Directory
        </h1>
        <p className="mt-1 text-sm text-mf-ink-soft">
          Every patient with a cached resource set on this deployment.
        </p>
      </header>

      <div className="mf-surface-card overflow-hidden">
        {isLoading && (
          <div className="p-5 space-y-3" aria-label="Loading directory">
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
          </div>
        )}

        {isError && (
          <p
            className="p-5 text-sm text-destructive"
            role="alert"
            data-testid="directory-error"
          >
            Failed to load directory
            {error instanceof Error ? `: ${error.message}` : "."}
          </p>
        )}

        {!isLoading && !isError && data && data.length === 0 && (
          <p className="p-5 text-sm text-mf-ink-soft" data-testid="directory-empty">
            No patients in cache yet.
          </p>
        )}

        {!isLoading && !isError && data && data.length > 0 && (
          <table className="w-full text-sm" data-testid="directory-table">
            <thead>
              <tr className="border-b-2 border-mf-ink bg-mf-paper-2">
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">
                  Patient ID
                </th>
              </tr>
            </thead>
            <tbody>
              {data.map((p) => (
                <tr
                  key={p.id}
                  className="border-b border-mf-paper-2 transition-colors last:border-0 hover:bg-mf-paper-2"
                >
                  <td className="px-4 py-3 align-middle">
                    <Link
                      href={`/patients/${encodeURIComponent(p.id)}/profile`}
                      className="font-mono font-semibold text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mf-accent"
                      data-testid={`directory-row-${p.id}`}
                    >
                      {p.id}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
