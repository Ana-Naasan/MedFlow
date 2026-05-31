"use client"

import { AlertTriangle, ExternalLink, FileText, Loader2, User } from "lucide-react"

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { useEvidence, useResource } from "@/lib/api/hooks"
import type { Citation, Span } from "@/lib/api/types"

interface EvidenceDrawerProps {
  /** The citation whose source to resolve, or null when nothing is open. */
  citation: Citation | null
  /** Backend patient id — needed to resolve `resource` citations. */
  patientId: string
  /** Open state controlled by the parent; closing clears the active citation. */
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * Parse a `resource` citation ref of the form "ResourceType/resourceId"
 * (e.g. "MedicationStatement/med-warfarin") into its two parts. Mirrors the
 * reference frontend's parsing. Returns empty parts when the ref is malformed
 * so the resolving query stays disabled rather than firing a bad request.
 */
function parseResourceRef(ref: string): { type: string; id: string } {
  const slash = ref.indexOf("/")
  if (slash <= 0 || slash === ref.length - 1) return { type: "", id: "" }
  return { type: ref.slice(0, slash), id: ref.slice(slash + 1) }
}

/**
 * The evidence drawer. Opens for the active citation and RESOLVES it:
 *   - `evidence` kind → GET /evidence/{id} (the ref IS the evidence id)
 *   - `resource` kind → GET the raw FHIR resource for this patient
 * When the citation carries a `source_span`, the PDF page + highlighted snippet
 * is rendered above the resolved body.
 *
 * Only one underlying query is ever enabled (gated by the active kind) so we
 * never fire a spurious request for the kind that isn't showing.
 */
export function EvidenceDrawer({
  citation,
  patientId,
  open,
  onOpenChange,
}: EvidenceDrawerProps) {
  const isKnowledge = citation?.kind === "evidence"
  const isResource = citation?.kind === "resource"

  const { type: resourceType, id: resourceId } = isResource
    ? parseResourceRef(citation!.ref)
    : { type: "", id: "" }

  const evidenceQuery = useEvidence(
    isKnowledge ? citation!.ref : "",
    open && isKnowledge
  )
  const resourceQuery = useResource(
    patientId,
    resourceType,
    resourceId,
    open && isResource
  )

  const span = citation?.source_span ?? null
  const title = citation?.label ?? citation?.ref ?? "Source"

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full gap-0 sm:max-w-md">
        <SheetHeader className="border-b border-border">
          <div className="flex items-center gap-2 pr-8">
            {isKnowledge ? (
              <ExternalLink
                size={16}
                aria-hidden="true"
                className="shrink-0 text-[var(--accent)]"
              />
            ) : (
              <User
                size={16}
                aria-hidden="true"
                className="shrink-0 text-[var(--text-secondary)]"
              />
            )}
            <SheetTitle className="truncate">{title}</SheetTitle>
          </div>
          <SheetDescription>
            {isKnowledge
              ? "External clinical knowledge backing this association."
              : "Source fact from the patient's record."}
          </SheetDescription>
        </SheetHeader>

        {/* tabIndex/aria-label let keyboard users focus and arrow-scroll this
            overflow region even when its content is purely non-interactive
            (e.g. a long FHIR-JSON <pre> or span highlight). */}
        <div
          className="flex-1 overflow-y-auto p-4"
          tabIndex={0}
          aria-label="Source detail"
        >
          {span && <SpanHighlight span={span} />}

          {citation == null ? null : isKnowledge ? (
            <EvidenceBody
              loading={evidenceQuery.isLoading}
              isError={evidenceQuery.isError}
              data={evidenceQuery.data}
              fallbackRef={citation.ref}
            />
          ) : isResource ? (
            resourceType.length === 0 ? (
              <DrawerNotice
                icon="warn"
                text="This citation reference could not be parsed into a resolvable resource."
              />
            ) : (
              <ResourceBody
                loading={resourceQuery.isLoading}
                isError={resourceQuery.isError}
                data={resourceQuery.data}
                resourceType={resourceType}
                resourceId={resourceId}
              />
            )
          ) : (
            <DrawerNotice
              icon="warn"
              text={`Unrecognized citation kind "${citation.kind}".`}
            />
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}

/**
 * Render the PDF page + the snippet with the [start,end] substring marked.
 * Ports the reference PdfHighlight: the snippet is shown verbatim with the
 * cited slice wrapped in a <mark>. Defends against an out-of-range span by
 * falling back to highlighting the whole snippet.
 */
function SpanHighlight({ span }: { span: Span }) {
  const { snippet, start, end, page } = span
  const inRange =
    Number.isInteger(start) &&
    Number.isInteger(end) &&
    start >= 0 &&
    end <= snippet.length &&
    start < end

  const before = inRange ? snippet.slice(0, start) : ""
  const mark = inRange ? snippet.slice(start, end) : snippet
  const after = inRange ? snippet.slice(end) : ""

  return (
    <div className="mb-4 rounded-lg border border-border bg-bg-subtle p-3">
      <p className="flex items-center gap-1.5 text-xs font-medium text-[var(--text-muted)]">
        <FileText size={12} aria-hidden="true" />
        PDF · Page {page}
      </p>
      <blockquote className="mt-2 text-sm leading-relaxed text-foreground">
        {before}
        <mark className="rounded-sm bg-[color-mix(in_oklch,var(--warning)_28%,transparent)] px-0.5 text-foreground">
          {mark}
        </mark>
        {after}
      </blockquote>
    </div>
  )
}

/**
 * Resolved knowledge-card body. The backend returns the raw card, which in
 * practice carries `{source, snippet, ref_url}` (looser than the declared
 * EvidenceSnippet), so we read fields defensively and never assume a shape.
 */
function EvidenceBody({
  loading,
  isError,
  data,
  fallbackRef,
}: {
  loading: boolean
  isError: boolean
  data: unknown
  fallbackRef: string
}) {
  if (loading) return <DrawerSkeleton label="Loading evidence…" />
  if (isError || data == null)
    return <DrawerNotice icon="warn" text="Source unavailable." />

  const card = data as Record<string, unknown>
  const source = typeof card.source === "string" ? card.source : null
  const snippet = typeof card.snippet === "string" ? card.snippet : null
  const refUrl = typeof card.ref_url === "string" ? card.ref_url : null
  const label = typeof card.label === "string" ? card.label : null

  const hasContent = source || snippet || refUrl || label

  return (
    <div className="space-y-3">
      {source && (
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {source}
        </p>
      )}
      {label && !source && (
        <p className="text-sm font-medium text-foreground">{label}</p>
      )}
      {snippet && (
        <p className="text-sm leading-relaxed text-foreground">{snippet}</p>
      )}
      {!hasContent && (
        <DrawerNotice
          icon="info"
          text={`Resolved evidence "${fallbackRef}" with no displayable content.`}
        />
      )}
      {refUrl && (
        <a
          href={refUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--accent)] hover:underline"
        >
          View source
          <ExternalLink size={13} aria-hidden="true" />
        </a>
      )}
    </div>
  )
}

/**
 * Resolved FHIR-resource body. The resource JSON is arbitrary, so we surface a
 * compact identity line plus the raw JSON for the clinician to inspect, rather
 * than guessing at a schema-specific rendering.
 */
function ResourceBody({
  loading,
  isError,
  data,
  resourceType,
  resourceId,
}: {
  loading: boolean
  isError: boolean
  data: unknown
  resourceType: string
  resourceId: string
}) {
  if (loading) return <DrawerSkeleton label="Loading record source…" />
  if (isError || data == null)
    return <DrawerNotice icon="warn" text="Source unavailable." />

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {resourceType} · {resourceId}
      </p>
      <pre className="overflow-x-auto rounded-lg border border-border bg-bg-subtle p-3 text-xs leading-relaxed text-foreground">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}

function DrawerSkeleton({ label }: { label: string }) {
  return (
    <div
      role="status"
      aria-label={label}
      className="flex items-center gap-2 text-sm text-muted-foreground"
    >
      <Loader2 size={16} className="animate-spin" aria-hidden="true" />
      {label}
    </div>
  )
}

function DrawerNotice({
  icon,
  text,
}: {
  icon: "warn" | "info"
  text: string
}) {
  return (
    <div className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
      {icon === "warn" ? (
        <AlertTriangle
          size={16}
          aria-hidden="true"
          className="mt-0.5 shrink-0 text-[var(--warning)]"
        />
      ) : (
        <FileText
          size={16}
          aria-hidden="true"
          className="mt-0.5 shrink-0 text-[var(--text-muted)]"
        />
      )}
      <p>{text}</p>
    </div>
  )
}
