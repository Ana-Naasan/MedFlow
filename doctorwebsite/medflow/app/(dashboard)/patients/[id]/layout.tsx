import { notFound } from "next/navigation"
import { getPatientById } from "@/lib/mock-data/patients"
import { PatientHeader } from "@/components/layout/PatientHeader"
import { PatientTabs } from "@/components/layout/PatientTabs"

interface PatientLayoutProps {
  children: React.ReactNode
  params: Promise<{ id: string }>
}

export default async function PatientLayout({
  children,
  params,
}: PatientLayoutProps) {
  const { id } = await params
  const patient = getPatientById(id)

  if (!patient) {
    notFound()
  }

  return (
    <div className="flex flex-col h-full">
      <div
        className="sticky top-0 z-20"
        style={{ background: "var(--mf-paper)" }}
      >
        <PatientHeader patient={patient} />
        <PatientTabs patientId={id} />
      </div>
      <div className="flex-1 overflow-auto px-6 py-6">
        {children}
      </div>
    </div>
  )
}
