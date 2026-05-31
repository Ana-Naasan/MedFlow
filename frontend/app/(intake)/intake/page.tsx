"use client";

import { useState } from "react";
import { apiClient } from "../../../lib/api/client";

interface IntakeResult {
  patient_id: string;
  status: string;
  resource_count: number;
  hypothesis_ids: string[];
}

export default function IntakePage() {
  const [connector, setConnector] = useState("mock-fhir");
  const [sourcePatientId, setSourcePatientId] = useState("");
  const [patientId, setPatientId] = useState("");
  const [result, setResult] = useState<IntakeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);

    const { data, error: apiError } = await apiClient.POST("/intake", {
      body: {
        connector,
        source_patient_id: sourcePatientId,
        ...(patientId ? { patient_id: patientId } : {}),
      },
    });

    setSubmitting(false);

    if (apiError) {
      setError(
        "detail" in (apiError as Record<string, unknown>)
          ? String((apiError as Record<string, unknown>).detail)
          : "Intake failed"
      );
    } else if (data) {
      setResult(data as unknown as IntakeResult);
    }
  }

  return (
    <main>
      <div className="shell">
        <section className="panel card stack">
          <div>
            <p className="eyebrow">Intake</p>
            <h1>Register patient data source</h1>
          </div>

          <form onSubmit={handleSubmit} className="stack" data-testid="intake-form">
            <label>
              Connector
              <select
                value={connector}
                onChange={(e) => setConnector(e.target.value)}
                data-testid="intake-connector"
              >
                <option value="mock-fhir">Mock FHIR</option>
                <option value="postgres-a">Postgres A</option>
              </select>
            </label>

            <label>
              Source patient ID
              <input
                type="text"
                value={sourcePatientId}
                onChange={(e) => setSourcePatientId(e.target.value)}
                placeholder="e.g. DEMO-001"
                required
                data-testid="intake-source-patient-id"
              />
            </label>

            <label>
              Our patient ID <span style={{ opacity: 0.6 }}>(optional — minted if blank)</span>
              <input
                type="text"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                placeholder="leave blank to auto-generate"
                data-testid="intake-patient-id"
              />
            </label>

            <button type="submit" disabled={submitting} data-testid="intake-submit">
              {submitting ? "Registering…" : "Register patient"}
            </button>
          </form>

          {error && (
            <p style={{ color: "red" }} role="alert" data-testid="intake-error">
              {error}
            </p>
          )}

          {result && (
            <div data-testid="intake-result">
              <p>
                <strong>Registered:</strong> <code>{result.patient_id}</code>
              </p>
              <p>
                <strong>Resources stored:</strong> {result.resource_count}
              </p>
              {result.hypothesis_ids.length > 0 && (
                <p>
                  <strong>Hypotheses seeded:</strong> {result.hypothesis_ids.length}
                </p>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
