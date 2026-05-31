import type { CareCategoryId, IntakeQuestion } from "./types"

export type CareCategoryIconKey = "brain" | "stethoscope" | "heart" | "briefcase"

export const CARE_CATEGORIES: readonly {
  id: CareCategoryId
  label: string
  subtitle: string
  iconKey: CareCategoryIconKey
}[] = [
  {
    id: "mental-health",
    label: "Mental Health",
    subtitle: "Stress, anxiety, mood, therapy",
    iconKey: "brain",
  },
  {
    id: "primary-care",
    label: "Primary Care",
    subtitle: "Illness, prescriptions, referrals",
    iconKey: "stethoscope",
  },
  {
    id: "wellness",
    label: "General Wellness",
    subtitle: "Habits, nutrition, sleep, fitness",
    iconKey: "heart",
  },
  {
    id: "work-life",
    label: "Work & Life Support",
    subtitle: "Legal, financial, relationships, career",
    iconKey: "briefcase",
  },
] as const

const INTAKE_BY_CATEGORY: Record<CareCategoryId, IntakeQuestion[]> = {
  "mental-health": [
    {
      id: "mh-topic",
      prompt: "What's been on your mind lately?",
      type: "chips",
      options: [
        "Stress",
        "Anxiety",
        "Low mood",
        "Sleep issues",
        "Something else",
      ],
    },
    {
      id: "mh-duration",
      prompt: "How long have you been feeling this way?",
      type: "chips",
      options: ["A few days", "1-2 weeks", "More than a month"],
    },
    {
      id: "mh-prior",
      prompt: "Have you spoken to a mental health professional before?",
      type: "yes-no",
      options: ["Yes", "No"],
    },
  ],
  "primary-care": [
    {
      id: "pc-symptom",
      prompt: "What are you experiencing?",
      type: "chips",
      options: [
        "Fever or infection",
        "Skin concern",
        "Chronic condition",
        "Prescription renewal",
        "Something else",
      ],
    },
    {
      id: "pc-duration",
      prompt: "How long have you had this concern?",
      type: "chips",
      options: ["Just started", "A few days", "Over a week"],
    },
    {
      id: "pc-urgent",
      prompt: "Is this urgent?",
      type: "chips",
      options: [
        "Yes, I need help today",
        "No, I can wait a day or two",
      ],
    },
  ],
  wellness: [
    {
      id: "wl-focus",
      prompt: "What would you like to work on?",
      type: "chips",
      options: ["Sleep", "Nutrition", "Fitness", "Stress", "All of the above"],
    },
    {
      id: "wl-habits",
      prompt: "How would you describe your current habits?",
      type: "chips",
      options: [
        "Pretty healthy",
        "Could be better",
        "Starting from scratch",
      ],
    },
  ],
  "work-life": [
    {
      id: "wl-area",
      prompt: "What area do you need support with?",
      type: "chips",
      options: [
        "Relationships",
        "Work stress",
        "Financial",
        "Legal",
        "Career",
      ],
    },
    {
      id: "wl-preference",
      prompt:
        "Would you prefer to speak with someone or access self-guided resources?",
      type: "chips",
      options: ["Talk to someone", "Self-guided", "Not sure"],
    },
  ],
}

export function getIntakeQuestions(category: CareCategoryId): IntakeQuestion[] {
  return INTAKE_BY_CATEGORY[category] ?? []
}

export function computeOutcome(
  category: CareCategoryId,
  answers: Record<string, string[]>
): "low-acuity" | "standard" {
  if (category === "work-life") {
    const pref = answers["wl-preference"]?.[0]
    if (pref === "Self-guided") return "low-acuity"
  }
  if (category === "primary-care") {
    const urgent = answers["pc-urgent"]?.[0]
    if (urgent === "No, I can wait a day or two") {
      const symptom = answers["pc-symptom"]?.[0]
      if (symptom === "Prescription renewal") return "low-acuity"
    }
  }
  if (category === "wellness") {
    const habits = answers["wl-habits"]?.[0]
    if (habits === "Pretty healthy") return "low-acuity"
  }
  return "standard"
}
