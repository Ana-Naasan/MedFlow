import type { PacketLoadDiagnostic } from "../lib/usePacket";

interface PacketLoadFailurePanelProps {
  diag: PacketLoadDiagnostic;
}

/**
 * Renders an explicit, actionable diagnostic for a packet-fetch failure.
 * Replaces the previous opaque "Failed to load packet." (see #90) so the
 * operator can see WHY the request failed without leaving the page.
 *
 * The hint heuristic maps the observed HTTP status to the most likely
 * misconfiguration — covering the failure modes that surfaced #90:
 *
 *   - 401   → bearer-token mismatch or missing NEXT_PUBLIC_API_TOKEN
 *   - 403   → token present but rejected (rare; same family)
 *   - 404   → wrong patient id OR wrong base URL routing to the wrong API
 *   - 5xx   → backend error (look at Cloud Run / server logs)
 *   - none  → no response at all: backend unreachable, CORS preflight
 *             failure, or wrong NEXT_PUBLIC_API_BASE_URL
 */
export function PacketLoadFailurePanel({ diag }: PacketLoadFailurePanelProps) {
  const hint = describeFailure(diag.status);
  const bodyText = formatBody(diag.body);

  return (
    <main>
      <div className="shell">
        <section
          className="panel card packet-failure"
          role="alert"
          aria-label="Packet load failure"
          data-testid="packet-load-failure"
        >
          <h2 className="packet-failure-title">Failed to load packet.</h2>
          <p className="packet-failure-hint">{hint}</p>

          <dl className="packet-failure-diag">
            <dt>Status</dt>
            <dd data-testid="packet-failure-status">
              {diag.status !== undefined ? String(diag.status) : "— (no response)"}
            </dd>
            <dt>URL</dt>
            <dd data-testid="packet-failure-url">{diag.url || "—"}</dd>
            <dt>Elapsed</dt>
            <dd data-testid="packet-failure-elapsed">{diag.elapsedMs} ms</dd>
            {bodyText !== null && (
              <>
                <dt>Response body</dt>
                <dd>
                  <pre
                    className="packet-failure-body"
                    data-testid="packet-failure-body"
                  >
                    {bodyText}
                  </pre>
                </dd>
              </>
            )}
          </dl>
        </section>
      </div>
    </main>
  );
}

function describeFailure(status: number | undefined): string {
  if (status === undefined) {
    return (
      "No response from the backend. Likely the API is unreachable, " +
      "NEXT_PUBLIC_API_BASE_URL is wrong, or a CORS preflight was blocked."
    );
  }
  if (status === 401 || status === 403) {
    return (
      "The backend rejected the request as unauthorized. Check that " +
      "NEXT_PUBLIC_API_TOKEN (frontend) matches DEV_TOKEN (backend) in this " +
      "deployment."
    );
  }
  if (status === 404) {
    return (
      "The backend returned 404 for this route. Either the patient id is " +
      "not recognised, or NEXT_PUBLIC_API_BASE_URL points to a different API."
    );
  }
  if (status >= 500) {
    return "The backend reported a server error. Check the backend logs.";
  }
  if (status >= 400) {
    return "The backend rejected the request.";
  }
  // 2xx-3xx getting here would mean the client treated success as failure.
  return "Unexpected non-error response routed through the failure UI.";
}

/**
 * Stringify an error body for display. Long bodies are truncated so a
 * surprise stacktrace doesn't blow up the page.
 */
function formatBody(body: unknown): string | null {
  if (body === null || body === undefined) return null;
  let text: string;
  if (typeof body === "string") {
    text = body;
  } else {
    try {
      text = JSON.stringify(body, null, 2);
    } catch {
      text = String(body);
    }
  }
  const trimmed = text.trim();
  if (!trimmed) return null;
  const max = 800;
  return trimmed.length > max ? trimmed.slice(0, max) + "\n… (truncated)" : trimmed;
}
