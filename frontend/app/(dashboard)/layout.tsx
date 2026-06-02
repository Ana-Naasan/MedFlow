import { Sidebar } from "@/components/layout/Sidebar"
import { Header } from "@/components/layout/Header"
import { PatientSearch } from "@/components/patients/PatientSearch"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="mf-body mf-clinical flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6" id="main-content">
          {children}
        </main>
      </div>
      {/* Global search modal — available on every dashboard page */}
      <PatientSearch />
    </div>
  )
}
