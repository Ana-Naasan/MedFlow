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

export function ClinicianLogin() {
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
        userType: "clinician",
        redirect: false,
      })
      if (result?.error) {
        setError("Invalid email or password. Please try again.")
      } else {
        router.push("/dashboard")
      }
    } catch {
      setError("An unexpected error occurred. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="mf-body flex min-h-dvh">
      <div
        className="hidden lg:flex lg:w-1/2 flex-col items-center justify-center gap-8 p-16"
        style={{
          background: "var(--mf-clinician)",
          borderRight: "2px solid var(--mf-clinician-line)",
        }}
      >
        <div className="flex flex-col items-center gap-4 text-center">
          <BrandLogo size="md" className="min-h-0 flex-col gap-2" />
          <h2 className="mf-display text-3xl font-semibold leading-tight">
            Practice without the noise
          </h2>
          <p className="max-w-sm text-sm" style={{ color: "var(--mf-ink-soft)" }}>
            Records, scheduling, and secure patient care in one calm clinical
            workspace.
          </p>
        </div>
        <ul className="flex flex-col gap-3 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          {[
            "Real-time patient monitoring",
            "Secure, HIPAA-aligned records",
            "AI-assisted clinical notes",
          ].map((item) => (
            <li key={item} className="flex items-center gap-2">
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full text-xs text-white"
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
            className="mb-6 inline-flex text-sm"
            style={{ color: "var(--mf-ink-soft)" }}
          >
            &larr; Back to home
          </Link>
          <motion.div
            initial={false}
            animate="visible"
            variants={{ visible: { transition: { staggerChildren: 0.08 } } }}
            className="flex flex-col gap-6"
          >
            <motion.div variants={itemVariants}>
              <p className="mf-eyebrow mb-2">Clinician sign in</p>
              <h1 className="mf-display text-2xl font-semibold">
                Sign in to Umraa
              </h1>
              <p className="mt-1 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
                Your clinical dashboard
              </p>
            </motion.div>

            <form onSubmit={handleSubmit} noValidate>
              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="email">Email address</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="dr.name@umraa.ca"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                    className="h-11 min-h-[44px] border-2 bg-[var(--mf-paper)]"
                    style={{ borderColor: "var(--mf-ink)" }}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="********"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      disabled={isLoading}
                      className="h-11 min-h-[44px] border-2 bg-[var(--mf-paper)] pr-10"
                      style={{ borderColor: "var(--mf-ink)" }}
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      onClick={() => setShowPassword((p) => !p)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2"
                      style={{ color: "var(--mf-ink-soft)" }}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                {error && (
                  <div
                    role="alert"
                    className="flex gap-2 rounded-lg border-2 px-3 py-2 text-sm"
                    style={{
                      borderColor: "var(--mf-patient-line)",
                      color: "var(--mf-ink)",
                    }}
                  >
                    <AlertCircle size={15} className="shrink-0" />
                    {error}
                  </div>
                )}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="mf-btn-primary w-full"
                >
                  {isLoading ? "Signing in..." : "Sign in"}
                </button>
              </div>
            </form>

            <div
              className="rounded-lg border-2 px-4 py-3 text-sm"
              style={{
                borderColor: "var(--mf-paper-2)",
                background: "var(--mf-paper-2)",
              }}
            >
              <p className="mb-1 font-medium">Demo credentials</p>
              <p>
                <span style={{ color: "var(--mf-ink-soft)" }}>Email: </span>
                <code className="font-mono text-xs" style={{ color: "var(--mf-accent)" }}>
                  dr.wu@umraa.ca
                </code>
              </p>
              <p>
                <span style={{ color: "var(--mf-ink-soft)" }}>Password: </span>
                <code className="font-mono text-xs" style={{ color: "var(--mf-accent)" }}>
                  password123
                </code>
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
