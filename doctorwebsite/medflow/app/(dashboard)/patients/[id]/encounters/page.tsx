import { notFound } from "next/navigation"
import { getPatientById } from "@/lib/mock-data/patients"

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function Page({ params }: PageProps) {
  const { id } = await params
  const patient = getPatientById(id)
  if (!patient) notFound()

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center gap-2">
      <p className="text-sm font-medium text-foreground">Coming soon</p>
      <p className="text-xs text-muted-foreground">
        This section is under construction.
      </p>
    </div>
  )
}
