import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <div className="shell">
        <section className="hero">
          <div className="panel hero-copy">
            <p className="eyebrow">Stage B scaffold</p>
            <h1 className="title">Umraa</h1>
            <p className="lede">
              A runnable baseline for the polypharmacy decision packet: contract-first backend,
              typed frontend client, and the database surfaces ready for the first four work
              streams to branch immediately.
            </p>
            <div className="actions">
              <Link className="button primary" href="/packet">
                Open provider packet
              </Link>
              <Link className="button secondary" href="/intake">
                Open intake flow
              </Link>
            </div>
          </div>

          <aside className="panel card stack">
            <div>
              <h2>Baseline services</h2>
              <p>
                Backend health, OpenAPI client stubs, and three Postgres services are in place.
              </p>
            </div>
            <div className="chip-row">
              <span className="chip">FastAPI</span>
              <span className="chip">Next.js</span>
              <span className="chip">TanStack Query</span>
              <span className="chip">Postgres x3</span>
            </div>
          </aside>
        </section>

        <section className="split">
          <article className="panel card">
            <h3>Provider surface</h3>
            <p>
              The packet view is the first contract consumer and will receive the verified,
              citation-backed decision packet once the reasoning layer lands.
            </p>
          </article>
          <article className="panel card">
            <h3>Intake surface</h3>
            <p>
              The intake flow gives the frontend team a clean route group and a typed client to
              build against while the API expands.
            </p>
          </article>
        </section>
      </div>
    </main>
  );
}