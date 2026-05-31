"use client"

import { useState } from "react"
import Link from "next/link"
import { CalendarDays, Clock, User, ChevronLeft, ChevronRight, Plus, Video, Stethoscope, UserCheck, Activity, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Textarea } from "@/components/ui/textarea"
import { patients } from "@/lib/mock-data/patients"

// ── Types ────────────────────────────────────────────────────────────────────

type AppointmentType = "office-visit" | "telehealth" | "walk-in" | "follow-up" | "procedure"
type AppointmentStatus = "confirmed" | "pending" | "cancelled" | "completed"

interface Appointment {
  id: string
  patientId: string
  patientName: string
  date: string
  time: string
  duration: number
  type: AppointmentType
  status: AppointmentStatus
  physician: string
  notes?: string
}

// ── Constants ────────────────────────────────────────────────────────────────

const TODAY = "2026-05-31"

const SEED_APPOINTMENTS: Appointment[] = [
  { id: "apt-001", patientId: "24884", patientName: "Whitmore, Harold", date: "2026-05-31", time: "09:00", duration: 30, type: "office-visit", status: "confirmed", physician: "Park, Eleanor" },
  { id: "apt-003", patientId: "10231", patientName: "Chen, Margaret", date: "2026-05-31", time: "10:00", duration: 45, type: "office-visit", status: "confirmed", physician: "Chen, James" },
  { id: "apt-004", patientId: "33591", patientName: "Patel, Raj", date: "2026-06-01", time: "09:00", duration: 30, type: "telehealth", status: "confirmed", physician: "Wu, Bella" },
  { id: "apt-005", patientId: "68103", patientName: "Morrison, Gerald", date: "2026-06-01", time: "10:30", duration: 60, type: "procedure", status: "pending", physician: "Chen, James" },
  { id: "apt-006", patientId: "57720", patientName: "Dubois, Sophie", date: "2026-06-02", time: "11:00", duration: 20, type: "follow-up", status: "confirmed", physician: "Wu, Bella" },
  { id: "apt-007", patientId: "24884", patientName: "Whitmore, Harold", date: "2026-06-02", time: "14:00", duration: 30, type: "office-visit", status: "confirmed", physician: "Park, Eleanor" },
  { id: "apt-008", patientId: "10231", patientName: "Chen, Margaret", date: "2026-06-03", time: "09:00", duration: 30, type: "telehealth", status: "pending", physician: "Chen, James" },
  { id: "apt-009", patientId: "33591", patientName: "Patel, Raj", date: "2026-06-03", time: "11:30", duration: 45, type: "office-visit", status: "confirmed", physician: "Wu, Bella" },
  { id: "apt-011", patientId: "68103", patientName: "Morrison, Gerald", date: "2026-06-04", time: "14:00", duration: 60, type: "office-visit", status: "confirmed", physician: "Chen, James" },
  { id: "apt-012", patientId: "57720", patientName: "Dubois, Sophie", date: "2026-06-04", time: "15:00", duration: 20, type: "walk-in", status: "completed", physician: "Wu, Bella" },
  { id: "apt-013", patientId: "24884", patientName: "Whitmore, Harold", date: "2026-06-05", time: "09:30", duration: 30, type: "follow-up", status: "confirmed", physician: "Park, Eleanor" },
  { id: "apt-014", patientId: "33591", patientName: "Patel, Raj", date: "2026-05-30", time: "10:00", duration: 30, type: "office-visit", status: "completed", physician: "Wu, Bella" },
  { id: "apt-015", patientId: "10231", patientName: "Chen, Margaret", date: "2026-05-29", time: "14:30", duration: 45, type: "telehealth", status: "completed", physician: "Chen, James" },
]

const TYPE_CONFIG: Record<AppointmentType, { bg: string; text: string; border: string; icon: React.ReactNode }> = {
  "office-visit": { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", icon: <Stethoscope className="size-3" /> },
  "telehealth":   { bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200", icon: <Video className="size-3" /> },
  "walk-in":      { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", icon: <UserCheck className="size-3" /> },
  "follow-up":    { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", icon: <Activity className="size-3" /> },
  "procedure":    { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", icon: <FileText className="size-3" /> },
}

const STATUS_CONFIG: Record<AppointmentStatus, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
  confirmed: { variant: "default", label: "Confirmed" },
  pending:   { variant: "secondary", label: "Pending" },
  cancelled: { variant: "destructive", label: "Cancelled" },
  completed: { variant: "outline", label: "Completed" },
}

const PHYSICIANS = ["Wu, Bella", "Chen, James", "Park, Eleanor"] as const
const DURATIONS = ["15", "20", "30", "45", "60"] as const
const APPOINTMENT_TYPES: AppointmentType[] = ["office-visit", "telehealth", "walk-in", "follow-up", "procedure"]
const DAY_HOURS = Array.from({ length: 11 }, (_, i) => i + 8) // 8–18

// ── Helpers ──────────────────────────────────────────────────────────────────

function getWeekDays(referenceDate: string): string[] {
  const d = new Date(referenceDate)
  const day = d.getDay()
  const monday = new Date(d)
  monday.setDate(d.getDate() - (day === 0 ? 6 : day - 1))
  return Array.from({ length: 7 }, (_, i) => {
    const dd = new Date(monday)
    dd.setDate(monday.getDate() + i)
    return dd.toISOString().slice(0, 10)
  })
}

function formatDisplayDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })
}

// ── AppointmentChip ──────────────────────────────────────────────────────────

function AppointmentChip({ apt, onClick }: { apt: Appointment; onClick: () => void }) {
  const c = TYPE_CONFIG[apt.type]
  const isCancelled = apt.status === "cancelled"
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left rounded-lg px-2.5 py-2 text-xs border transition-all hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-1 ${c.bg} ${c.text} ${c.border} ${isCancelled ? "opacity-40 line-through" : ""}`}
    >
      <p className="font-semibold truncate flex items-center gap-1">
        {c.icon}
        {apt.time} — {apt.patientName}
      </p>
      <p className="opacity-75 mt-0.5 capitalize">{apt.type.replace(/-/g, " ")}</p>
    </button>
  )
}

// ── BookingModal ─────────────────────────────────────────────────────────────

interface BookingModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onBook: (apt: Appointment) => void
}

function BookingModal({ open, onOpenChange, onBook }: BookingModalProps) {
  const [form, setForm] = useState({
    patientId: "",
    date: TODAY,
    time: "09:00",
    duration: "30",
    type: "office-visit" as AppointmentType,
    physician: "Wu, Bella" as string,
    notes: "",
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.patientId) return
    const patient = patients.find(p => p.id === form.patientId)
    const patientName = patient ? `${patient.name.last}, ${patient.name.first}` : "Unknown"
    const newApt: Appointment = {
      id: `apt-${Date.now()}`,
      patientId: form.patientId,
      patientName,
      date: form.date,
      time: form.time,
      duration: parseInt(form.duration),
      type: form.type,
      status: "confirmed",
      physician: form.physician,
      notes: form.notes || undefined,
    }
    onBook(newApt)
    onOpenChange(false)
    setForm({ patientId: "", date: TODAY, time: "09:00", duration: "30", type: "office-visit", physician: "Wu, Bella", notes: "" })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New Appointment</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 pt-1">
          {/* Patient */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-foreground">Patient <span className="text-destructive">*</span></label>
            <Select value={form.patientId} onValueChange={(v) => setForm(prev => ({ ...prev, patientId: v ?? "" }))}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select patient…" />
              </SelectTrigger>
              <SelectContent>
                {patients.map(p => (
                  <SelectItem key={p.id} value={p.id}>{p.name.last}, {p.name.first}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Date + Time */}
          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-foreground">Date <span className="text-destructive">*</span></label>
              <Input type="date" value={form.date} onChange={e => setForm(prev => ({ ...prev, date: e.target.value }))} required />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-foreground">Time <span className="text-destructive">*</span></label>
              <Input type="time" value={form.time} onChange={e => setForm(prev => ({ ...prev, time: e.target.value }))} required />
            </div>
          </div>

          {/* Duration + Type */}
          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-foreground">Duration</label>
              <Select value={form.duration} onValueChange={(v) => setForm(prev => ({ ...prev, duration: v ?? "30" }))}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DURATIONS.map(d => <SelectItem key={d} value={d}>{d} min</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-foreground">Type</label>
              <Select value={form.type} onValueChange={(v) => setForm(prev => ({ ...prev, type: (v ?? "office-visit") as AppointmentType }))}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {APPOINTMENT_TYPES.map(t => (
                    <SelectItem key={t} value={t}>{t.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Physician */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-foreground">Physician</label>
            <Select value={form.physician} onValueChange={(v) => setForm(prev => ({ ...prev, physician: v ?? "Wu, Bella" }))}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PHYSICIANS.map(ph => <SelectItem key={ph} value={ph}>{ph}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {/* Notes */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-foreground">Notes <span className="text-muted-foreground">(optional)</span></label>
            <Textarea placeholder="Add any notes…" value={form.notes} onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))} className="min-h-[72px]" />
          </div>

          <div className="-mx-4 -mb-4 flex justify-end gap-2 border-t bg-muted/50 px-4 py-3 rounded-b-xl">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={!form.patientId}>Book Appointment</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ── AppointmentDetailSheet ───────────────────────────────────────────────────

function AppointmentDetailSheet({
  apt,
  open,
  onOpenChange,
}: {
  apt: Appointment | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  if (!apt) return null
  const typeLabel = apt.type.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
  const { variant, label } = STATUS_CONFIG[apt.status]

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[400px] sm:max-w-[400px] p-0 flex flex-col gap-0">
        <SheetHeader className="border-b px-5 py-4">
          <SheetTitle className="text-base">Appointment Details</SheetTitle>
        </SheetHeader>

        <div className="flex flex-col gap-5 px-5 py-5 overflow-y-auto flex-1">
          {/* Patient */}
          <div className="flex flex-col gap-0.5">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Patient</p>
            <Link
              href={`/patients/${apt.patientId}/profile`}
              className="font-semibold text-foreground hover:text-primary transition-colors"
            >
              {apt.patientName}
            </Link>
          </div>

          {/* Time + Duration */}
          <div className="flex flex-col gap-0.5">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Time</p>
            <p className="flex items-center gap-1.5 text-sm text-foreground">
              <Clock className="size-3.5 text-muted-foreground" />
              {apt.time} · {apt.duration} min
            </p>
          </div>

          {/* Type + Status */}
          <div className="flex gap-2 flex-wrap">
            <Badge variant="secondary" className="capitalize">{typeLabel}</Badge>
            <Badge variant={variant}>{label}</Badge>
          </div>

          {/* Physician */}
          <div className="flex flex-col gap-0.5">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Physician</p>
            <p className="flex items-center gap-1.5 text-sm text-foreground">
              <User className="size-3.5 text-muted-foreground" />
              {apt.physician}
            </p>
          </div>

          {/* Notes */}
          {apt.notes && (
            <div className="flex flex-col gap-0.5">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Notes</p>
              <p className="text-sm text-foreground rounded-lg bg-muted/50 px-3 py-2 border">{apt.notes}</p>
            </div>
          )}
        </div>

        <div className="border-t px-5 py-4 flex gap-2">
          <Button variant="outline" className="flex-1">Reschedule</Button>
          <Button variant="ghost" className="flex-1 text-destructive hover:text-destructive hover:bg-destructive/10">Cancel</Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}

// ── WeekView ─────────────────────────────────────────────────────────────────

function WeekView({
  weekDays,
  appointments,
  onSelectApt,
}: {
  weekDays: string[]
  appointments: Appointment[]
  onSelectApt: (apt: Appointment) => void
}) {
  return (
    <div className="border border-border rounded-xl overflow-hidden bg-white">
      {/* Header */}
      <div className="grid grid-cols-7 border-b border-border">
        {weekDays.map(date => {
          const d = new Date(date)
          const isToday = date === TODAY
          return (
            <div key={date} className={`p-3 text-center border-r border-border last:border-0 ${isToday ? "bg-primary/5" : ""}`}>
              <p className="text-xs text-muted-foreground">{d.toLocaleDateString("en", { weekday: "short" })}</p>
              <p className={`text-lg font-semibold mt-0.5 ${isToday ? "text-primary" : "text-foreground"}`}>{d.getDate()}</p>
            </div>
          )
        })}
      </div>

      {/* Body */}
      <div className="grid grid-cols-7 divide-x divide-border min-h-[500px]">
        {weekDays.map(date => {
          const dayAppts = appointments
            .filter(a => a.date === date)
            .sort((a, b) => a.time.localeCompare(b.time))
          const isToday = date === TODAY
          return (
            <div key={date} className={`p-2 space-y-1.5 ${isToday ? "bg-primary/[0.02]" : ""}`}>
              {dayAppts.map(apt => (
                <AppointmentChip key={apt.id} apt={apt} onClick={() => onSelectApt(apt)} />
              ))}
              {dayAppts.length === 0 && (
                <p className="text-xs text-muted-foreground text-center mt-4">—</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── DayView ──────────────────────────────────────────────────────────────────

function DayView({
  date,
  appointments,
  onSelectApt,
}: {
  date: string
  appointments: Appointment[]
  onSelectApt: (apt: Appointment) => void
}) {
  const dayAppts = appointments
    .filter(a => a.date === date)
    .sort((a, b) => a.time.localeCompare(b.time))

  // Group appointments by their starting hour bucket
  const byHour = DAY_HOURS.reduce<Record<number, Appointment[]>>((acc, h) => {
    acc[h] = dayAppts.filter(a => {
      const apptHour = parseInt(a.time.split(":")[0], 10)
      return apptHour === h
    })
    return acc
  }, {})

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-white">
      {/* Date header */}
      <div className="h-10 border-b border-border bg-muted/30 flex items-center px-4">
        <span className="text-xs font-medium text-muted-foreground">
          {new Date(date).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
        </span>
      </div>

      <div className="grid grid-cols-[80px_1fr] divide-x divide-border">
        {/* Hour labels */}
        <div className="flex flex-col">
          {DAY_HOURS.map(hour => (
            <div key={hour} className="h-16 border-b border-border last:border-0 flex items-start justify-end pr-3 pt-1">
              <span className="text-xs text-muted-foreground tabular-nums">{String(hour).padStart(2, "0")}:00</span>
            </div>
          ))}
        </div>

        {/* Appointment slots */}
        <div className="flex flex-col">
          {DAY_HOURS.map(hour => {
            const slotAppts = byHour[hour] ?? []
            return (
              <div key={hour} className="h-16 border-b border-border last:border-0 px-2 py-1 flex flex-col gap-1 overflow-hidden">
                {slotAppts.map(apt => {
                  const c = TYPE_CONFIG[apt.type]
                  const isCancelled = apt.status === "cancelled"
                  return (
                    <button
                      key={apt.id}
                      type="button"
                      onClick={() => onSelectApt(apt)}
                      className={`w-full text-left rounded-md px-2 py-0.5 text-xs border transition-all hover:shadow-sm focus-visible:outline-2 flex items-center gap-1.5 ${c.bg} ${c.text} ${c.border} ${isCancelled ? "opacity-40 line-through" : ""}`}
                    >
                      {c.icon}
                      <span className="font-semibold truncate">{apt.time}</span>
                      <span className="truncate opacity-90">— {apt.patientName}</span>
                      <span className="ml-auto opacity-60 shrink-0">{apt.duration}m</span>
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>

      {dayAppts.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-10">No appointments scheduled for this day.</p>
      )}
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function SchedulerPage() {
  const [appointments, setAppointments] = useState<Appointment[]>(SEED_APPOINTMENTS)
  const [view, setView] = useState<"week" | "day">("week")
  const [selectedApt, setSelectedApt] = useState<Appointment | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [bookingOpen, setBookingOpen] = useState(false)
  const [currentWeekRef, setCurrentWeekRef] = useState(TODAY)

  const weekDays = getWeekDays(currentWeekRef)

  function shiftWeek(direction: -1 | 1) {
    const d = new Date(currentWeekRef)
    d.setDate(d.getDate() + direction * 7)
    setCurrentWeekRef(d.toISOString().slice(0, 10))
  }

  function handleSelectApt(apt: Appointment) {
    setSelectedApt(apt)
    setDetailOpen(true)
  }

  function handleBook(apt: Appointment) {
    setAppointments(prev => [...prev, apt])
  }

  const todayCount = appointments.filter(a => a.date === TODAY && a.status !== "cancelled").length
  const weekCount = appointments.filter(a => weekDays.includes(a.date) && a.status !== "cancelled").length

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Top bar */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Scheduler</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{formatDisplayDate(TODAY)}</p>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex items-center rounded-lg border border-border bg-white p-0.5 gap-0.5">
            <button
              type="button"
              onClick={() => setView("week")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${view === "week" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
            >
              <CalendarDays className="size-3.5" />
              Week
            </button>
            <button
              type="button"
              onClick={() => setView("day")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${view === "day" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
            >
              <Clock className="size-3.5" />
              Day
            </button>
          </div>
          <Button onClick={() => setBookingOpen(true)}>
            <Plus className="size-4" />
            New Appointment
          </Button>
        </div>
      </div>

      {/* Stats strip */}
      <div className="flex gap-4">
        {[
          { label: "Today", value: todayCount, sub: "appointments" },
          { label: "This week", value: weekCount, sub: "appointments" },
          { label: "Physicians", value: PHYSICIANS.length, sub: "on schedule" },
        ].map(stat => (
          <div key={stat.label} className="rounded-xl border border-border bg-white px-4 py-3 flex flex-col gap-0.5 min-w-[110px]">
            <p className="text-xs text-muted-foreground">{stat.label}</p>
            <p className="text-xl font-semibold text-foreground tabular-nums">{stat.value}</p>
            <p className="text-xs text-muted-foreground">{stat.sub}</p>
          </div>
        ))}
      </div>

      {/* Calendar nav */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon-sm" onClick={() => shiftWeek(-1)} aria-label="Previous week">
            <ChevronLeft className="size-4" />
          </Button>
          <Button variant="outline" size="icon-sm" onClick={() => shiftWeek(1)} aria-label="Next week">
            <ChevronRight className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="ml-1 text-xs"
            onClick={() => setCurrentWeekRef(TODAY)}
          >
            Today
          </Button>
        </div>
        <p className="text-sm font-medium text-foreground">
          {new Date(weekDays[0]).toLocaleDateString("en-US", { month: "long", year: "numeric" })}
        </p>
      </div>

      {/* Calendar body */}
      {view === "week" ? (
        <WeekView weekDays={weekDays} appointments={appointments} onSelectApt={handleSelectApt} />
      ) : (
        <DayView date={TODAY} appointments={appointments} onSelectApt={handleSelectApt} />
      )}

      {/* Detail Sheet */}
      <AppointmentDetailSheet apt={selectedApt} open={detailOpen} onOpenChange={setDetailOpen} />

      {/* Booking Modal */}
      <BookingModal open={bookingOpen} onOpenChange={setBookingOpen} onBook={handleBook} />
    </div>
  )
}
