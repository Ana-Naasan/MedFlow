"use client";

import { useState } from "react";

import { apiClient } from "../../../lib/api/client";
import type { components } from "../../../lib/api/generated";

type IntakeResponse = components["schemas"]["IntakeResponse"];

export default function IntakePage() {
  const [connector, setConnector] = useState("mock-fhir");
  const [sourcePatientId, setSourcePatientId] = useState("DEMO-001");
  const [patientId, setPatientId] = useState("");
  const [result, setResult] = useState<IntakeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);

    const { data, error: apiError, response } = await apiClient.POST("/intake", {
      body: {
        connector,
        source_patient_id: sourcePatientId,
        ...(patientId ? { patient_id: patientId } : {}),
      },
    });

    setSubmitting(false);

    if (apiError || !response.ok) {
      setError(
        (apiError as { detail?: string } | undefined)?.detail ??
          `Request failed: ${response.status}`,
      );
    } else if (data) {
      setResult(data);
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

          <form onSubmit={handleSubmit} className="stack">
            <label>
              Connector
              <input
                value={connector}
                onChange={(e) => setConnector(e.target.value)}
                placeholder="mock-fhir"
                required
              />
            </label>

            <label>
              Source patient ID
              <input
                value={sourcePatientId}
                onChange={(e) => setSourcePatientId(e.target.value)}
                placeholder="DEMO-001"
                required
              />
            </label>

            <label>
              Patient ID override
              <input
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                placeholder="optional — auto-generated if blank"
              />
            </label>

            <button type="submit" disabled={submitting}>
              {submitting ? "Registering…" : "Register"}
            </button>
          </form>

          {error && (
            <div className="chip" style={{ color: "var(--color-danger, red)" }}>
              Error: {error}
            </div>
          )}

          {result && (
            <div className="stack">
              <p className="eyebrow">Registered</p>
              <div className="chip-row">
                <span className="chip">ID: {result.patient_id}</span>
                <span className="chip">{result.resource_count} resources</span>
                <span className="chip">{(result.hypothesis_ids ?? []).length} hypotheses</span>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
