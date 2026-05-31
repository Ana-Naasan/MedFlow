"use client"

import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { FlowProgress } from "@/components/patient/FlowProgress"
import {
  computeOutcome,
  getIntakeQuestions,
} from "@/lib/patient-flow/intake-questions"
import type { IntakeQuestion } from "@/lib/patient-flow/types"
import { useMedFlowStore } from "@/lib/store"

export default function IntakePage() {
  const router = useRouter()
  const category = useMedFlowStore((s) => s.patientCareCategory)
  const answers = useMedFlowStore((s) => s.patientIntakeAnswers)
  const setAnswer = useMedFlowStore((s) => s.setPatientIntakeAnswer)
  const setOutcome = useMedFlowStore((s) => s.setPatientOutcome)

  const [step, setStep] = useState(0)
  const [evaluating, setEvaluating] = useState(false)
  const [lowAcuityView, setLowAcuityView] = useState(false)

  const questions = category ? getIntakeQuestions(category) : []
  const totalSteps = questions.length + 1

  useEffect(() => {
    if (!category) router.replace("/patient/care-select")
  }, [category, router])

  if (!category) return null

  if (evaluating) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4 text-center">
        <div
          className="size-10 animate-spin rounded-full border-2 border-t-transparent"
          style={{ borderColor: "var(--mf-accent)", borderTopColor: "transparent" }}
          aria-hidden="true"
        />
        <p className="mf-display text-xl font-semibold">
          Finding the right care for you...
        </p>
      </div>
    )
  }

  if (lowAcuityView) {
    return (
      <div className="space-y-6">
        <FlowProgress current={totalSteps} total={totalSteps} label="Almost done" />
        <div
          className="rounded-xl border-2 p-6"
          style={{ borderColor: "var(--mf-accent)", background: "var(--mf-accent-soft)" }}
        >
          <h2 className="mf-display text-2xl font-semibold mb-2">
            You might find this helpful
          </h2>
          <p className="text-sm mb-4" style={{ color: "var(--mf-ink-soft)" }}>
            Based on your answers, these self-guided resources could be a good
            first step. You can still book a visit if you&apos;d prefer to talk
            with someone.
          </p>
          <ul className="list-disc pl-5 text-sm space-y-1 mb-6">
            <li>Short guided exercises for stress and sleep</li>
            <li>Articles written in plain language</li>
            <li>Check-in tools you can use on your own time</li>
          </ul>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              className="mf-btn-secondary flex-1"
              onClick={() => router.push("/patient/dashboard")}
            >
              Explore resources
            </button>
            <button
              type="button"
              className="mf-btn-primary flex-1"
              onClick={() => {
                setOutcome("standard")
                router.push("/patient/booking")
              }}
            >
              Book a visit anyway
            </button>
          </div>
        </div>
      </div>
    )
  }

  const q = questions[step] as IntakeQuestion | undefined

  function finishIntake(finalAnswers: Record<string, string[]>) {
    if (!category) return
    setEvaluating(true)
    window.setTimeout(() => {
      const outcome = computeOutcome(category, finalAnswers)
      setOutcome(outcome)
      setEvaluating(false)
      if (outcome === "low-acuity") {
        setLowAcuityView(true)
      } else {
        router.push("/patient/booking")
      }
    }, 1500)
  }

  function handleChipSelect(question: IntakeQuestion, option: string) {
    setAnswer(question.id, [option])
  }

  function goNext() {
    if (!q) return
    const nextAnswers = { ...answers, [q.id]: answers[q.id] ?? [] }
    if (step < questions.length - 1) {
      setStep((s) => s + 1)
    } else {
      finishIntake(nextAnswers)
    }
  }

  function goBack() {
    if (step === 0) {
      router.push("/patient/care-select")
    } else {
      setStep((s) => s - 1)
    }
  }

  const canContinue =
    q &&
    (q.type === "text"
      ? (answers[q.id]?.[0]?.trim().length ?? 0) > 0
      : (answers[q.id]?.length ?? 0) > 0)

  return (
    <div className="space-y-8">
      <FlowProgress
        current={step + 1}
        total={questions.length}
        label={`Step ${step + 1} of ${questions.length}`}
      />
      {q && (
        <>
          <div>
            <h1 className="mf-display text-2xl font-semibold sm:text-[28px]">
              {q.prompt}
            </h1>
          </div>

          {q.type === "text" && (
            <textarea
              className="w-full min-h-[100px] rounded-lg border-2 p-3 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
              style={{ borderColor: "var(--mf-ink)", background: "var(--mf-paper)" }}
              placeholder="Tell us in your own words..."
              value={answers[q.id]?.[0] ?? ""}
              onChange={(e) => setAnswer(q.id, [e.target.value])}
              aria-label={q.prompt}
            />
          )}

          {(q.type === "chips" || q.type === "yes-no") && q.options && (
            <div className="flex flex-wrap gap-3" role="group" aria-label={q.prompt}>
              {q.options.map((opt) => {
                const selected = answers[q.id]?.includes(opt)
                return (
                  <button
                    key={opt}
                    type="button"
                    data-selected={selected}
                    className="mf-chip"
                    onClick={() => handleChipSelect(q, opt)}
                    aria-pressed={selected}
                  >
                    {opt}
                  </button>
                )
              })}
            </div>
          )}

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
            <button type="button" onClick={goBack} className="mf-btn-secondary">
              Back
            </button>
            <button
              type="button"
              disabled={!canContinue}
              onClick={goNext}
              className="mf-btn-primary"
            >
              {step < questions.length - 1 ? "Next" : "Continue"}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
