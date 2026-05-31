import { Sidebar } from "../../components/layout/Sidebar";

/**
 * Clinician shell. Sidebar nav on the left, main content on the right.
 * Mirrors medflow's (dashboard)/layout.tsx but without the global
 * PatientSearch modal and without next-auth signOut (we're using
 * bearer-token auth, not sessions).
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-mf-paper text-foreground">
      <Sidebar />
      <div className="flex flex-1 min-w-0 flex-col overflow-hidden">
        <main
          className="flex-1 overflow-y-auto p-4 sm:p-6"
          id="main-content"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
