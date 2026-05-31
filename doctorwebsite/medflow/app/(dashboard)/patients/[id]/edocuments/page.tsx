"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { motion, type Variants } from "framer-motion"
import { Download, Printer, Mail } from "lucide-react"

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { getEDocumentsByPatientId } from "@/lib/mock-data/edocuments"
import type { EDocument, EDocType, EDocStatus } from "@/lib/types"

// ─── Animation ───────────────────────────────────────────────────────────────

const pageVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.25, 0.1, 0.25, 1] },
  },
}

// ─── Config ──────────────────────────────────────────────────────────────────

const DOC_TYPE_CONFIG: Record<EDocType, { bg: string; text: string; label: string }> = {
  "lab-report": { bg: "bg-primary/10", text: "text-primary", label: "Lab Report" },
  "referral-letter": { bg: "bg-purple-100", text: "text-purple-700", label: "Referral" },
  "imaging-report": { bg: "bg-warning/10", text: "text-warning", label: "Imaging" },
  "consent-form": { bg: "bg-muted", text: "text-muted-foreground", label: "Consent" },
  "discharge-summary": { bg: "bg-teal-100", text: "text-teal-700", label: "Discharge" },
}

const STATUS_CONFIG: Record<EDocStatus, { dot: string; text: string; bg: string; label: string }> = {
  received: { dot: "bg-success", text: "text-success", bg: "bg-success/10", label: "Received" },
  sent: { dot: "bg-primary", text: "text-primary", bg: "bg-primary/10", label: "Sent" },
  pending: { dot: "bg-warning", text: "text-warning", bg: "bg-warning/10", label: "Pending" },
}

function StatusBadge({ status }: { status: EDocStatus }) {
  const c = STATUS_CONFIG[status]
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

function DocTypeBadge({ docType }: { docType: EDocType }) {
  const c = DOC_TYPE_CONFIG[docType]
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  )
}

// ─── Viewer modal ─────────────────────────────────────────────────────────────

interface EDocViewerProps {
  doc: EDocument | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function EDocViewer({ doc, open, onOpenChange }: EDocViewerProps) {
  if (!doc) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl w-full p-0 overflow-hidden">
        <DialogHeader className="px-5 pt-5 pb-4 border-b border-border">
          <DialogTitle className="text-sm font-medium text-foreground pr-8">
            {doc.subject}
          </DialogTitle>
        </DialogHeader>

        <div className="flex min-h-0 max-h-[70vh]">
          {/* Document body */}
          <div className="flex-1 overflow-y-auto bg-bg-subtle p-4">
            <pre className="text-xs text-foreground whitespace-pre-wrap font-mono leading-relaxed">
              {doc.content}
            </pre>
          </div>

          {/* Metadata sidebar */}
          <div className="w-60 shrink-0 border-l border-border bg-bg-surface p-4 space-y-4 overflow-y-auto">
            <div className="flex flex-col gap-2">
              <DocTypeBadge docType={doc.docType} />
              <StatusBadge status={doc.status} />
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <p className="text-muted-foreground mb-0.5">Date</p>
                <p className="font-medium text-foreground font-mono">{doc.date}</p>
              </div>
              <div>
                <p className="text-muted-foreground mb-0.5">From</p>
                <p className="font-medium text-foreground">{doc.sender}</p>
              </div>
              <div>
                <p className="text-muted-foreground mb-0.5">To</p>
                <p className="font-medium text-foreground">{doc.recipient}</p>
              </div>
              {doc.faxNumber && (
                <div>
                  <p className="text-muted-foreground mb-0.5">Fax</p>
                  <p className="font-medium text-foreground font-mono">{doc.faxNumber}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 px-5 py-3 border-t border-border bg-bg-surface">
          <Button variant="outline" size="sm" className="gap-1.5">
            <Download className="w-3.5 h-3.5" />
            Download
          </Button>
          <Button variant="ghost" size="sm" className="gap-1.5">
            <Printer className="w-3.5 h-3.5" />
            Print
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function EDocumentsPage() {
  const { id } = useParams<{ id: string }>()
  const docs = getEDocumentsByPatientId(id).sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  )

  const [selectedDoc, setSelectedDoc] = useState<EDocument | null>(null)
  const [viewerOpen, setViewerOpen] = useState(false)
  const [activeSubTab, setActiveSubTab] = useState("careconnect")

  function openDoc(doc: EDocument) {
    setSelectedDoc(doc)
    setViewerOpen(true)
  }

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate">
      <Tabs value={activeSubTab} onValueChange={setActiveSubTab}>
        <TabsList>
          <TabsTrigger value="careconnect">CareConnect</TabsTrigger>
          <TabsTrigger value="compose">Compose Fax/Zip</TabsTrigger>
        </TabsList>

        {/* CareConnect — documents list */}
        <TabsContent value="careconnect" className="mt-4">
          {docs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 gap-4">
              <svg width="64" height="64" viewBox="0 0 64 64" fill="none" aria-hidden="true">
                <rect x="10" y="16" width="44" height="32" rx="3" stroke="var(--border)" strokeWidth="2" />
                <path d="M10 19l22 16 22-16" stroke="var(--border)" strokeWidth="2" fill="none" />
              </svg>
              <p className="text-sm font-medium text-foreground">No electronic documents</p>
              <p className="text-xs text-muted-foreground">Incoming and outgoing documents will appear here</p>
            </div>
          ) : (
            <div className="bg-bg-surface border border-border rounded-xl overflow-hidden">
              {/* header row */}
              <div className="hidden md:grid grid-cols-[90px_110px_1fr_1.2fr_110px_70px] gap-3 px-4 py-2.5 border-b border-border bg-muted/40 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                <span>Date</span>
                <span>Type</span>
                <span>Subject</span>
                <span>From / To</span>
                <span>Status</span>
                <span></span>
              </div>
              {docs.map((doc) => (
                <button
                  key={doc.id}
                  type="button"
                  onClick={() => openDoc(doc)}
                  className="w-full grid grid-cols-1 md:grid-cols-[90px_110px_1fr_1.2fr_110px_70px] gap-1 md:gap-3 md:items-center px-4 py-3 border-b border-border last:border-0 hover:bg-bg-subtle transition-colors text-left"
                >
                  <span className="font-mono text-xs text-muted-foreground">{doc.date}</span>
                  <span><DocTypeBadge docType={doc.docType} /></span>
                  <span className="text-sm text-foreground truncate">{doc.subject}</span>
                  <span className="text-xs text-muted-foreground truncate">
                    {doc.sender} → {doc.recipient}
                  </span>
                  <span><StatusBadge status={doc.status} /></span>
                  <span className="text-xs text-primary font-medium md:text-right">View</span>
                </button>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Compose */}
        <TabsContent value="compose" className="mt-4">
          <div className="max-w-md space-y-4 py-6">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Mail className="w-4 h-4" />
              Compose and send a fax or zip package
            </div>
            <Input placeholder="Recipient fax number..." disabled />
            <Input placeholder="Subject..." disabled />
            <Textarea placeholder="Cover note..." rows={4} disabled className="resize-none" />
            <Button variant="default" disabled>
              Send Fax
            </Button>
          </div>
        </TabsContent>
      </Tabs>

      <EDocViewer doc={selectedDoc} open={viewerOpen} onOpenChange={setViewerOpen} />
    </motion.div>
  )
}
