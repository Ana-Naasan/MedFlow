"use client"

import { useMemo } from "react"
import Link from "next/link"
import {
  Bell,
  CalendarDays,
  CheckSquare,
  FileText,
  FlaskConical,
  StickyNote,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import {
  CLINICIAN_NOTIFICATIONS,
  type ClinicianNotification,
  type NotificationType,
} from "@/lib/mock-data/notifications"
import { useMedFlowStore } from "@/lib/store"

const TYPE_ICONS: Record<
  NotificationType,
  React.ComponentType<{ className?: string }>
> = {
  lab: FlaskConical,
  edocument: FileText,
  appointment: CalendarDays,
  task: CheckSquare,
  memo: StickyNote,
}

function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60_000)
  const diffHours = Math.floor(diffMs / 3_600_000)
  const diffDays = Math.floor(diffMs / 86_400_000)

  if (diffMins < 1) return "Just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString("en-CA", { month: "short", day: "numeric" })
}

function NotificationRow({
  notification,
  unread,
  onRead,
}: {
  notification: ClinicianNotification
  unread: boolean
  onRead: (id: string) => void
}) {
  const Icon = TYPE_ICONS[notification.type]

  return (
    <Link
      href={notification.href}
      onClick={() => onRead(notification.id)}
      className={cn(
        "flex gap-3 rounded-md px-2 py-2.5 text-left transition-colors",
        "hover:bg-[var(--mf-paper-2)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]",
        unread && "bg-[var(--mf-accent-soft)]/40"
      )}
    >
      <span
        className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border"
        style={{
          borderColor: "var(--mf-paper-2)",
          background: "var(--mf-paper)",
          color: "var(--mf-accent)",
        }}
      >
        <Icon className="size-4" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-start justify-between gap-2">
          <span
            className={cn(
              "text-sm leading-snug",
              unread ? "font-semibold text-[var(--mf-ink)]" : "font-medium text-[var(--mf-ink)]"
            )}
          >
            {notification.title}
          </span>
          <span
            className="shrink-0 text-[10px] uppercase tracking-wide"
            style={{ color: "var(--mf-ink-soft)" }}
          >
            {formatRelativeTime(notification.createdAt)}
          </span>
        </span>
        <span
          className="mt-0.5 block text-xs leading-relaxed"
          style={{ color: "var(--mf-ink-soft)" }}
        >
          {notification.message}
        </span>
      </span>
      {unread && (
        <span
          className="mt-2 size-2 shrink-0 rounded-full"
          style={{ background: "var(--mf-accent)" }}
          aria-hidden
        />
      )}
    </Link>
  )
}

export function NotificationsMenu() {
  const readNotificationIds = useMedFlowStore((s) => s.readNotificationIds)
  const markNotificationRead = useMedFlowStore((s) => s.markNotificationRead)
  const markAllNotificationsRead = useMedFlowStore((s) => s.markAllNotificationsRead)

  const unreadCount = useMemo(
    () =>
      CLINICIAN_NOTIFICATIONS.filter((n) => !readNotificationIds.includes(n.id))
        .length,
    [readNotificationIds]
  )

  return (
    <DropdownMenu>
      <div className="relative">
        <DropdownMenuTrigger
          className="flex min-h-[44px] min-w-[44px] cursor-pointer items-center justify-center rounded-lg border-2 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 data-popup-open:bg-[var(--mf-paper-2)]"
          style={{
            borderColor: "var(--mf-ink)",
            color: "var(--mf-ink-soft)",
          }}
          aria-label={
            unreadCount > 0
              ? `Notifications, ${unreadCount} unread`
              : "Notifications"
          }
        >
          <Bell className="size-4" aria-hidden />
        </DropdownMenuTrigger>
        {unreadCount > 0 && (
          <span
            className="pointer-events-none absolute -top-0.5 -right-0.5 flex min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-semibold leading-4 text-white"
            style={{ background: "var(--mf-accent)" }}
            aria-hidden
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </div>

      <DropdownMenuContent
        align="end"
        sideOffset={8}
        className="w-[min(100vw-2rem,22rem)] border-2 p-0 shadow-lg ring-0"
        style={{
          borderColor: "var(--mf-ink)",
          background: "var(--mf-paper)",
        }}
      >
        <div
          className="flex items-center justify-between gap-2 border-b px-3 py-2.5"
          style={{ borderColor: "var(--mf-paper-2)" }}
        >
          <p className="mf-display text-sm font-semibold text-[var(--mf-ink)]">
            Notifications
          </p>
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault()
                markAllNotificationsRead()
              }}
              className="text-xs font-semibold hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]"
              style={{ color: "var(--mf-accent)" }}
            >
              Mark all read
            </button>
          )}
        </div>

        <div className="max-h-80 overflow-y-auto p-1.5">
          {CLINICIAN_NOTIFICATIONS.length === 0 ? (
            <p
              className="px-2 py-6 text-center text-sm"
              style={{ color: "var(--mf-ink-soft)" }}
            >
              No notifications
            </p>
          ) : (
            <ul className="flex flex-col gap-0.5" role="list">
              {CLINICIAN_NOTIFICATIONS.map((notification) => {
                const unread = !readNotificationIds.includes(notification.id)
                return (
                  <li key={notification.id}>
                    <NotificationRow
                      notification={notification}
                      unread={unread}
                      onRead={markNotificationRead}
                    />
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
