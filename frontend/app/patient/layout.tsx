import { PatientTopNav } from "@/components/patient/PatientTopNav"

export default function PatientLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="mf-body flex min-h-dvh flex-col">
      <PatientTopNav />
      <main className="flex-1 px-4 py-8 sm:px-6" id="main-content">
        <div className="mx-auto w-full max-w-2xl">{children}</div>
      </main>
    </div>
  )
}
