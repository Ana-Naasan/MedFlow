import { patients } from "@/lib/mock-data/patients"
import Link from "next/link"

export default function DirectoryPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <p className="mf-eyebrow mb-1">Clinician</p>
        <h1 className="mf-display text-2xl font-semibold leading-tight">
          Patient Directory
        </h1>
      </div>
      <div className="mf-surface-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr
              className="border-b-2"
              style={{
                borderColor: "var(--mf-ink)",
                background: "var(--mf-paper-2)",
              }}
            >
              <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">
                Name
              </th>
              <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">
                DOB
              </th>
              <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">
                Location
              </th>
              <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">
                Physician
              </th>
            </tr>
          </thead>
          <tbody>
            {patients.map((p) => (
              <tr
                key={p.id}
                className="border-b transition-colors last:border-0 hover:bg-[var(--mf-paper-2)]"
                style={{ borderColor: "var(--mf-paper-2)" }}
              >
                <td className="px-4 py-3 align-middle">
                  <Link
                    href={`/patients/${p.id}/profile`}
                    className="font-semibold hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]"
                    style={{ color: "var(--mf-accent)" }}
                  >
                    {p.name.last}, {p.name.first}
                  </Link>
                  <span
                    className="ml-2 font-mono text-xs"
                    style={{ color: "var(--mf-ink-soft)" }}
                  >
                    #{p.id}
                  </span>
                </td>
                <td
                  className="px-4 py-3 align-middle"
                  style={{ color: "var(--mf-ink-soft)" }}
                >
                  {p.dob}
                </td>
                <td
                  className="px-4 py-3 align-middle"
                  style={{ color: "var(--mf-ink-soft)" }}
                >
                  {p.location}
                </td>
                <td
                  className="px-4 py-3 align-middle"
                  style={{ color: "var(--mf-ink-soft)" }}
                >
                  {p.primaryPhysician}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
