import type { CareProvider } from "./types"

function addDays(base: Date, days: number): Date {
  const d = new Date(base)
  d.setDate(d.getDate() + days)
  return d
}

function slot(
  dayOffset: number,
  hour: number,
  minute: number,
  modality: "video" | "phone" | "in-person"
) {
  const start = addDays(new Date(), dayOffset)
  start.setHours(hour, minute, 0, 0)
  const end = new Date(start)
  end.setMinutes(end.getMinutes() + 30)
  return {
    id: `${dayOffset}-${hour}${minute}-${modality}`,
    start: start.toISOString(),
    end: end.toISOString(),
    modality,
  }
}

export const MOCK_PROVIDERS: CareProvider[] = [
  {
    id: "prov-1",
    name: "Dr. Amélie Fortin",
    credential: "RN, Mental Health Counsellor",
    bio: "Warm, practical support for stress, anxiety, and everyday mental health.",
    languages: ["EN", "FR"],
    modalities: ["video", "phone"],
    slots: [
      slot(1, 9, 0, "video"),
      slot(1, 11, 30, "video"),
      slot(2, 14, 0, "phone"),
      slot(3, 10, 0, "video"),
      slot(4, 16, 0, "video"),
    ],
  },
  {
    id: "prov-2",
    name: "Dr. James Okonkwo",
    credential: "MD, Family Medicine",
    bio: "Same-day virtual visits for common concerns, renewals, and referrals.",
    languages: ["EN"],
    modalities: ["video", "phone", "in-person"],
    slots: [
      slot(0, 13, 0, "video"),
      slot(1, 15, 0, "video"),
      slot(2, 9, 30, "in-person"),
      slot(3, 11, 0, "phone"),
      slot(5, 8, 30, "video"),
    ],
  },
  {
    id: "prov-3",
    name: "Sophie Laroche",
    credential: "Wellness Coach",
    bio: "Habit-building and lifestyle support for sleep, nutrition, and balance.",
    languages: ["EN", "FR"],
    modalities: ["video", "phone"],
    slots: [
      slot(1, 8, 0, "video"),
      slot(2, 12, 0, "video"),
      slot(4, 9, 0, "phone"),
      slot(6, 17, 0, "video"),
    ],
  },
]

export function getProvider(id: string): CareProvider | undefined {
  return MOCK_PROVIDERS.find((p) => p.id === id)
}
