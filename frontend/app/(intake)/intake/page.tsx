export default function IntakePage() {
  return (
    <main>
      <div className="shell">
        <section className="panel card stack">
          <div>
            <p className="eyebrow">Intake</p>
            <h1>Entry shell</h1>
            <p>
              This route will become the patient intake entry point. For now it proves the app
              router, styling, and client bundle are all wired.
            </p>
          </div>
          <div className="chip-row">
            <span className="chip">Typed API client</span>
            <span className="chip">Next app router</span>
            <span className="chip">Contract-first</span>
          </div>
        </section>
      </div>
    </main>
  );
}