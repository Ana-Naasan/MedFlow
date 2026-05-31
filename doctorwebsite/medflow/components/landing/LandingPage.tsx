"use client"

import Link from "next/link"
import { useState } from "react"
import { useSession } from "next-auth/react"
import { motion } from "framer-motion"
import { Heart, Stethoscope } from "lucide-react"
import { BrandLogo } from "@/components/brand/BrandLogo"

type Role = "patient" | "clinician"

const ROLE_STORAGE_KEY = "umraa-preferred-role"

/**
 * Read the stored role preference once, on first render. Guarded for SSR
 * (`typeof window`) so the server render and the client's initial render agree.
 */
function readStoredRole(): Role {
  if (typeof window === "undefined") return "patient"
  const stored = window.localStorage.getItem(ROLE_STORAGE_KEY)
  return stored === "clinician" ? "clinician" : "patient"
}

export function LandingPage() {
  const { data: session } = useSession()
  // Lazy initializer reads localStorage on first render instead of mirroring it
  // into state via a mount effect (no synchronous setState in an effect body).
  const [role, setRole] = useState<Role>(readStoredRole)

  const dashboardHref =
    session?.user?.userType === "patient"
      ? "/patient/dashboard"
      : session
        ? "/dashboard"
        : null

  function selectRole(next: Role) {
    setRole(next)
    localStorage.setItem(ROLE_STORAGE_KEY, next)
  }

  return (
    <div className="mf-body flex min-h-dvh flex-col">
      <div
        className="shrink-0 border-b-2 px-4 py-3"
        style={{
          background: "var(--mf-ink)",
          borderColor: "var(--mf-ink)",
        }}
      >
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <p className="mf-display text-sm font-medium text-[var(--mf-paper)]">
            First - who are you?
          </p>
          <div
            className="flex overflow-hidden rounded-lg border-2 border-[var(--mf-paper)]"
            role="group"
            aria-label="Choose your role"
          >
            <button
              type="button"
              onClick={() => selectRole("patient")}
              className="min-h-[44px] px-4 text-sm font-semibold transition-colors"
              style={{
                background:
                  role === "patient" ? "var(--mf-patient)" : "transparent",
                color: role === "patient" ? "var(--mf-ink)" : "var(--mf-paper)",
              }}
              aria-pressed={role === "patient"}
            >
              I&apos;m a patient
            </button>
            <button
              type="button"
              onClick={() => selectRole("clinician")}
              className="min-h-[44px] border-l border-[var(--mf-paper)]/25 px-4 text-sm font-semibold transition-colors"
              style={{
                background:
                  role === "clinician"
                    ? "var(--mf-clinician)"
                    : "transparent",
                color:
                  role === "clinician" ? "var(--mf-ink)" : "var(--mf-paper)",
              }}
              aria-pressed={role === "clinician"}
            >
              I&apos;m a clinician
            </button>
          </div>
        </div>
      </div>

      <main className="flex flex-1 flex-col items-center justify-center px-4 py-12 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
          className="w-full max-w-4xl space-y-10 text-center"
        >
          <div className="flex flex-col items-center gap-4">
            <BrandLogo
              size="lg"
              className="min-h-0 flex-col items-center gap-3"
            />
            <p className="mf-eyebrow">Virtual care for every employee</p>
            <p
              className="mx-auto max-w-lg text-[15px]"
              style={{ color: "var(--mf-ink-soft)" }}
            >
              Clinical-grade care, calmly delivered - mental health, primary
              care, and everyday wellness in one trusted platform.
            </p>
            {dashboardHref && (
              <Link
                href={dashboardHref}
                className="mf-btn-secondary mt-2 inline-flex text-sm"
              >
                Already signed in? Go to your dashboard
              </Link>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 sm:gap-[18px]">
            <Link
              href="/login/patient"
              onClick={() => selectRole("patient")}
              className="mf-card-selectable flex flex-col gap-3 p-6 text-left transition-opacity sm:p-8"
              style={{
                background: "var(--mf-patient)",
                borderColor: "var(--mf-patient-line)",
                opacity: role === "patient" ? 1 : 0.5,
              }}
              aria-label="I'm a Patient - get started"
            >
              <Heart
                className="size-8 shrink-0"
                style={{ color: "var(--mf-accent)" }}
                aria-hidden="true"
                strokeWidth={1.75}
              />
              <div>
                <p className="mf-eyebrow mb-1">For patients</p>
                <h2 className="mf-display text-2xl font-semibold sm:text-[32px]">
                  Get care in minutes
                </h2>
                <p
                  className="mt-2 text-sm"
                  style={{ color: "var(--mf-ink-soft)" }}
                >
                  Book virtual visits, check in on your well-being, and access
                  support when you&apos;re ready.
                </p>
              </div>
              <span className="mf-btn-primary mt-auto w-fit">Get started</span>
            </Link>

            <Link
              href="/login/clinician"
              onClick={() => selectRole("clinician")}
              className="mf-card-selectable flex flex-col gap-3 p-6 text-left transition-opacity sm:p-8"
              style={{
                background: "var(--mf-clinician)",
                borderColor: "var(--mf-clinician-line)",
                opacity: role === "clinician" ? 1 : 0.5,
              }}
              aria-label="I'm a Clinician - sign in"
            >
              <Stethoscope
                className="size-8 shrink-0"
                style={{ color: "var(--mf-accent)" }}
                aria-hidden="true"
                strokeWidth={1.75}
              />
              <div>
                <p className="mf-eyebrow mb-1">For clinicians</p>
                <h2 className="mf-display text-2xl font-semibold sm:text-[32px]">
                  Practice without the noise
                </h2>
                <p
                  className="mt-2 text-sm"
                  style={{ color: "var(--mf-ink-soft)" }}
                >
                  Your clinical dashboard - records, scheduling, and secure
                  patient care in one place.
                </p>
              </div>
              <span className="mf-btn-primary mt-auto w-fit">Sign in</span>
            </Link>
          </div>
        </motion.div>
      </main>
    </div>
  )
}
