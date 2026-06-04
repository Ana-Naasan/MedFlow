"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { signIn } from "next-auth/react"
import { motion, type Variants } from "framer-motion"
import { AlertCircle, Eye, EyeOff } from "lucide-react"
import Link from "next/link"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { BrandLogo } from "@/components/brand/BrandLogo"

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: [0.25, 0.1, 0.25, 1] },
  },
}

export function PatientLogin() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setIsLoading(true)
    try {
      const result = await signIn("credentials", {
        email,
        password,
        userType: "patient",
        redirect: false,
      })
      if (result?.error) {
        setError("We couldn't sign you in. Please check your details and try again.")
      } else {
        router.push("/patient/care-select")
      }
    } catch {
      setError("Something went wrong. Please try again in a moment.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="mf-body flex min-h-dvh">
      <div
        className="hidden lg:flex lg:w-1/2 flex-col items-center justify-center gap-8 p-16"
        style={{
          background: "var(--mf-patient)",
          borderRight: "2px solid var(--mf-patient-line)",
        }}
      >
        <div className="flex flex-col items-center gap-4 text-center">
          <BrandLogo size="md" className="min-h-0 flex-col gap-2" />
          <h2 className="mf-display text-3xl font-semibold leading-tight">
            Welcome back
          </h2>
          <p style={{ color: "var(--mf-ink-soft)" }} className="max-w-sm text-sm">
            Your care team is here when you need them. Book visits, message
            providers, and track your well-being.
          </p>
        </div>
        <ul className="flex flex-col gap-3 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          {[
            "Book care in minutes",
            "Private, secure messaging",
            "Support on your schedule",
          ].map((item) => (
            <li key={item} className="flex items-center gap-2.5">
              <span
                className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs text-white"
                style={{ background: "var(--mf-accent)" }}
                aria-hidden="true"
              >
                &#10003;
              </span>
              {item}
            </li>
          ))}
        </ul>
      </div>
      <div
        className="flex w-full lg:w-1/2 items-center justify-center p-6 sm:p-10"
        style={{ background: "var(--mf-paper)" }}
      >
        <div className="w-full max-w-sm">
          <Link
            href="/"
            className="mb-6 inline-flex items-center gap-1 text-sm"
            style={{ color: "var(--mf-ink-soft)" }}
          >
            <span aria-hidden="true">&larr;</span> Back to home
          </Link>
          <motion.div
            initial={false}
            animate="visible"
            variants={{ visible: { transition: { staggerChildren: 0.08 } } }}
            className="flex flex-col gap-6"
          >
            <motion.div variants={itemVariants}>
              <p className="mf-eyebrow mb-2">Patient sign in</p>
              <h1 className="mf-display text-2xl font-semibold leading-tight">
                Let&apos;s get you care
              </h1>
              <p className="mt-1 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
                Sign in to continue to your visit
              </p>
            </motion.div>
            <form onSubmit={handleSubmit} noValidate>
              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="patient-email">Email</Label>
                  <Input
                    id="patient-email"
                    type="email"
                    placeholder="you@example.com"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                    className="h-11 min-h-[44px] bg-[var(--mf-paper)]"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="patient-password">Password</Label>
                  <div className="relative">
                    <Input
                      id="patient-password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      disabled={isLoading}
                      className="h-11 min-h-[44px] pr-10 bg-[var(--mf-paper)]"
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      onClick={() => setShowPassword((p) => !p)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                {error && (
                  <div
                    role="alert"
                    className="flex gap-2 rounded-lg border px-3 py-2 text-sm"
                    style={{
                      borderColor: "var(--mf-patient-line)",
                      color: "var(--mf-ink)",
                    }}
                  >
                    <AlertCircle size={15} className="shrink-0" />
                    {error}
                  </div>
                )}
                <button type="submit" disabled={isLoading} className="mf-btn-primary w-full">
                  {isLoading ? "Signing in..." : "Continue"}
                </button>
              </div>
            </form>
            <div
              className="rounded-lg border px-4 py-3 text-sm"
              style={{
                borderColor: "var(--mf-paper-2)",
                background: "var(--mf-paper-2)",
              }}
            >
              <p className="font-medium mb-1">Demo account</p>
              <p>
                <span style={{ color: "var(--mf-ink-soft)" }}>Email: </span>
                <code className="font-mono text-xs">patient@medflow.ca</code>
              </p>
              <p>
                <span style={{ color: "var(--mf-ink-soft)" }}>Password: </span>
                <code className="font-mono text-xs">password123</code>
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
