"use client"

import { useEffect } from "react"
import { createPortal } from "react-dom"
// `Image` is aliased to `ImageIcon` so jsx-a11y/alt-text does not mistake the
// Lucide SVG icon for an <img> element requiring an `alt` prop.
import {
  FileText,
  Image as ImageIcon,
  Scan,
  File,
  Download,
  ExternalLink,
  X,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button, buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { FileRecord, FileType } from "@/lib/types"

// ─── Helpers ──────────────────────────────────────────────────────────────────

const FILE_TYPE_LABELS: Record<FileType, string> = {
  pdf: "PDF Document",
  dicom: "DICOM Image",
  image: "Image",
  document: "Document",
}

function formatBytes(kb: number): string {
  if (kb < 1024) return `${kb} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

function formatUploadDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-CA", {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

function resolvePreviewUrl(file: FileRecord): string | null {
  if (file.url) return file.url
  if (file.type === "pdf" && file.patientId === "24884") {
    return `/records/whitmore/${file.name}`
  }
  return null
}

function pdfViewerUrl(url: string): string {
  const base = url.split("#")[0]
  return `${base}#view=FitH&toolbar=1&navpanes=0`
}

function FileTypeIcon({ type }: { type: FileType }) {
  const iconProps = { className: "w-12 h-12 text-muted-foreground opacity-40" }
  switch (type) {
    case "pdf":
      return <FileText {...iconProps} />
    case "dicom":
      return <Scan {...iconProps} />
    case "image":
      return <ImageIcon {...iconProps} />
    default:
      return <File {...iconProps} />
  }
}

interface MetaRowProps {
  label: string
  value: string
}

function MetaRow({ label, value }: MetaRowProps) {
  return (
    <div className="space-y-0.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xs font-medium text-foreground break-words">{value}</p>
    </div>
  )
}

// ─── Fullscreen PDF (portal — not constrained by dialog CSS) ─────────────────

interface PdfFullscreenProps {
  file: FileRecord
  previewUrl: string
  onClose: () => void
}

function PdfFullscreenViewer({ file, previewUrl, onClose }: PdfFullscreenProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    document.body.style.overflow = "hidden"
    window.addEventListener("keydown", onKey)
    return () => {
      document.body.style.overflow = ""
      window.removeEventListener("keydown", onKey)
    }
  }, [onClose])

  return createPortal(
    <div className="fixed inset-0 z-[200] flex flex-col">
      <button
        type="button"
        aria-label="Close preview"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={file.name}
        className="relative z-10 m-3 flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl bg-popover shadow-2xl ring-1 ring-foreground/10 md:m-4"
        style={{ height: "calc(100vh - 1.5rem)", maxHeight: "calc(100vh - 1.5rem)" }}
      >
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-2.5">
          <div className="min-w-0 flex-1 pr-2">
            <p className="truncate text-sm font-medium text-foreground">{file.name}</p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {FILE_TYPE_LABELS[file.type]} · {formatBytes(file.sizeKb)} ·{" "}
              {file.uploadedBy} · {formatUploadDate(file.uploadedAt)}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <a
              href={previewUrl}
              download={file.name}
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "gap-1.5",
              )}
            >
              <Download className="size-3.5" />
              Download
            </a>
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({ variant: "ghost", size: "sm" }),
                "gap-1.5",
              )}
            >
              <ExternalLink className="size-3.5" />
              New tab
            </a>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={onClose}
              aria-label="Close"
            >
              <X className="size-4" />
            </Button>
          </div>
        </div>
        <iframe
          src={pdfViewerUrl(previewUrl)}
          title={file.name}
          className="min-h-0 w-full flex-1 border-0 bg-neutral-800"
        />
      </div>
    </div>,
    document.body,
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

interface FilePreviewModalProps {
  file: FileRecord | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function FilePreviewModal({
  file,
  open,
  onOpenChange,
}: FilePreviewModalProps) {
  if (!file) return null

  const previewUrl = resolvePreviewUrl(file)
  const showPdfViewer = file.type === "pdf" && previewUrl != null

  if (showPdfViewer) {
    if (!open) return null
    return (
      <PdfFullscreenViewer
        file={file}
        previewUrl={previewUrl}
        onClose={() => onOpenChange(false)}
      />
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-5 py-4 pr-12">
          <DialogTitle className="truncate text-sm font-medium text-foreground">
            {file.name}
          </DialogTitle>
        </DialogHeader>

        <div className="flex min-h-64">
          <div className="flex flex-1 flex-col items-center justify-center gap-3 bg-bg-subtle p-8">
            <FileTypeIcon type={file.type} />
            <p className="text-sm text-muted-foreground">
              Document preview not available
            </p>
          </div>

          <div className="w-52 shrink-0 space-y-4 border-l border-border bg-bg-surface p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              File Info
            </h3>
            <div className="space-y-3">
              <MetaRow label="Filename" value={file.name} />
              <MetaRow label="Type" value={FILE_TYPE_LABELS[file.type]} />
              <MetaRow label="Size" value={formatBytes(file.sizeKb)} />
              <MetaRow label="Uploaded by" value={file.uploadedBy} />
              <MetaRow label="Date" value={formatUploadDate(file.uploadedAt)} />
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
