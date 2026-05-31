"use client";

import { useParams } from "next/navigation";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../../../../components/ui/Card";
import { Skeleton } from "../../../../../components/ui/Skeleton";
import { usePatientResource } from "../../../../../lib/usePatientResource";

interface PatientResource {
  resourceType?: string;
  id?: string;
  gender?: string;
  birthDate?: string;
  identifier?: Array<{ system?: string; value?: string }>;
}

/**
 * Profile tab. Fetches `Patient/{id}` (the FHIR resource) and shows the
 * demographic fields the backend currently surfaces — id, gender,
 * birthDate, MRN. Mirrors medflow's Profile tab structure (demographics
 * card) but bound to live data instead of the mock-data store.
 */
export default function ProfilePage() {
  const params = useParams<{ id: string }>();
  const patientId = decodeURIComponent(params.id);
  const { data, isLoading, isError, error } = usePatientResource(
    patientId,
    "Patient",
    patientId,
  );
  const resource = (data ?? undefined) as PatientResource | undefined;
  const mrn = resource?.identifier?.find((i) =>
    (i.system ?? "").toLowerCase().includes("mrn"),
  )?.value;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="mf-eyebrow mb-1">Profile</p>
        <h2 className="mf-display text-2xl font-semibold leading-tight text-foreground">
          Demographics
        </h2>
      </header>

      <Card data-testid="profile-card">
        <CardHeader>
          <CardTitle>Patient details</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="space-y-3" aria-label="Loading profile">
              <Skeleton className="h-6 w-1/3" />
              <Skeleton className="h-6 w-1/2" />
              <Skeleton className="h-6 w-1/4" />
            </div>
          )}

          {isError && (
            <p
              className="text-sm text-destructive"
              role="alert"
              data-testid="profile-error"
            >
              Failed to load profile
              {error instanceof Error ? `: ${error.message}` : "."}
            </p>
          )}

          {!isLoading && !isError && resource && (
            <dl
              className="grid grid-cols-[120px_1fr] gap-y-3 gap-x-6 text-sm"
              data-testid="profile-fields"
            >
              <Field label="Patient ID" value={resource.id ?? patientId} mono />
              <Field
                label="Resource type"
                value={resource.resourceType ?? "Patient"}
              />
              {mrn && <Field label="MRN" value={mrn} mono />}
              {resource.gender && (
                <Field label="Gender" value={resource.gender} />
              )}
              {resource.birthDate && (
                <Field label="Birth date" value={resource.birthDate} mono />
              )}
            </dl>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <>
      <dt className="text-mf-ink-soft">{label}</dt>
      <dd className={mono ? "font-mono text-foreground" : "text-foreground"}>
        {value}
      </dd>
    </>
  );
}
