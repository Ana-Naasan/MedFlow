"use client"

import { useState, useEffect, useRef } from "react"
import { useParams } from "next/navigation"
import { useEditor, EditorContent } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Placeholder from "@tiptap/extension-placeholder"
import {
  FileEdit,
  Bold,
  Italic,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Lock,
  Unlock,
  Search,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import { getNotesByPatientId } from "@/lib/mock-data/notes"
import type { NoteTag } from "@/lib/types"

interface Note {
  id: string
  patientId: string
  date: string
  author: string
  title: string
  content: string
  tags: NoteTag[]
  lastEditedAt: string
}

type AutoSaveStatus = "saved" | "saving" | "unsaved"

const TAG_LABELS: Record<NoteTag, string> = {
  clinical: "Clinical",
  admin: "Admin",
  referral: "Referral",
  prescription: "Prescription",
}

const TAG_COLORS: Record<NoteTag, string> = {
  clinical: "bg-blue-50 text-blue-700",
  admin: "bg-gray-100 text-gray-600",
  referral: "bg-purple-50 text-purple-700",
  prescription: "bg-green-50 text-green-700",
}

type FilterTag = NoteTag | "all"
const FILTER_TAGS: FilterTag[] = ["all", "clinical", "admin", "referral", "prescription"]

export default function NotesPage() {
  const params = useParams()
  const id = typeof params.id === "string" ? params.id : Array.isArray(params.id) ? params.id[0] : ""

  const rawNotes = getNotesByPatientId(id) as Note[]

  const [localNotes, setLocalNotes] = useState<Note[]>(rawNotes)
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null)
  const [isLocked, setIsLocked] = useState(false)
  const [autoSave, setAutoSave] = useState<AutoSaveStatus>("saved")
  const [searchQuery, setSearchQuery] = useState("")
  const [filterTag, setFilterTag] = useState<FilterTag>("all")

  const saveTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const selectedNote = localNotes.find((n) => n.id === selectedNoteId) ?? null
  // Title is derived from the selected note during render (the title input is
  // key-reset per note id so it picks up the new value on selection) — no
  // effect-driven state mirroring.
  const editTitle = selectedNote?.title ?? ""

  const filteredNotes = localNotes.filter((note) => {
    const matchesSearch =
      searchQuery === "" ||
      note.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      note.content.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesTag = filterTag === "all" || note.tags.includes(filterTag)
    return matchesSearch && matchesTag
  })

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "Start writing your note..." }),
    ],
    content: selectedNote?.content ?? "",
    editable: !isLocked,
    onUpdate: () => {
      setAutoSave("unsaved")
      clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(() => {
        setAutoSave("saving")
        setTimeout(() => setAutoSave("saved"), 400)
      }, 1000)
    },
  })

  useEffect(() => {
    if (editor && selectedNote) {
      editor.commands.setContent(selectedNote.content)
      editor.setEditable(!isLocked)
    }
  }, [selectedNote?.id, isLocked]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectNote = (noteId: string) => {
    setSelectedNoteId(noteId)
    setIsLocked(false)
    setAutoSave("saved")
  }

  const handleTitleChange = (value: string) => {
    if (!selectedNoteId) return
    setLocalNotes((prev) =>
      prev.map((n) =>
        n.id === selectedNoteId ? { ...n, title: value } : n
      )
    )
    setAutoSave("unsaved")
    clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      setAutoSave("saving")
      setTimeout(() => setAutoSave("saved"), 400)
    }, 1000)
  }

  const handleNewNote = () => {
    const blank: Note = {
      id: `note-new-${Date.now()}`,
      patientId: id,
      date: new Date().toISOString().slice(0, 10),
      author: "Dr. Bella Wu",
      title: "Untitled Note",
      content: "",
      tags: ["clinical"],
      lastEditedAt: new Date().toISOString(),
    }
    setLocalNotes((prev) => [blank, ...prev])
    setSelectedNoteId(blank.id)
    setIsLocked(false)
  }

  const autoSaveLabel: Record<AutoSaveStatus, string> = {
    saved: "Saved",
    saving: "Saving…",
    unsaved: "Unsaved changes",
  }

  const autoSaveColor: Record<AutoSaveStatus, string> = {
    saved: "text-[var(--text-muted)]",
    saving: "text-[var(--text-secondary)]",
    unsaved: "text-amber-500",
  }

  return (
    <>
      <style>{`
        .ProseMirror { outline: none; min-height: 250px; font-size: 0.875rem; line-height: 1.6; }
        .ProseMirror p.is-editor-empty:first-child::before { content: attr(data-placeholder); float: left; color: var(--text-muted); pointer-events: none; height: 0; }
        .ProseMirror h2 { font-size: 1.1rem; font-weight: 600; margin: 1rem 0 0.4rem; }
        .ProseMirror h3 { font-size: 1rem; font-weight: 600; margin: 0.75rem 0 0.3rem; }
        .ProseMirror ul, .ProseMirror ol { padding-left: 1.5rem; margin: 0.25rem 0; }
        .ProseMirror li { margin: 0.15rem 0; }
        .ProseMirror strong { font-weight: 600; }
      `}</style>

      {/* Break out of parent's px-6 py-6 to use full height */}
      <div className="flex h-full overflow-hidden -mx-6 -my-6">

        {/* ── Left pane ── */}
        <div className="w-72 shrink-0 flex flex-col border-r border-[var(--border)] bg-[var(--bg-surface)] h-full overflow-hidden">

          {/* Search */}
          <div className="p-3 border-b border-[var(--border)]">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-[var(--text-muted)]" />
              <Input
                placeholder="Search notes…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 h-8 text-xs bg-[var(--bg-subtle)]"
              />
            </div>
          </div>

          {/* Tag filter chips */}
          <div className="flex flex-wrap gap-1.5 px-3 py-2 border-b border-[var(--border)]">
            {FILTER_TAGS.map((tag) => (
              <button
                key={tag}
                onClick={() => setFilterTag(tag)}
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors ${
                  filterTag === tag
                    ? "bg-[var(--primary)] text-white"
                    : "bg-[var(--bg-subtle)] text-muted-foreground hover:bg-muted"
                }`}
              >
                {tag === "all" ? "All" : TAG_LABELS[tag]}
              </button>
            ))}
          </div>

          {/* Note list */}
          <div className="flex-1 overflow-y-auto">
            {filteredNotes.length === 0 ? (
              <p className="text-xs text-[var(--text-muted)] text-center mt-8 px-4">
                No notes match your filters.
              </p>
            ) : (
              filteredNotes.map((note) => (
                <button
                  key={note.id}
                  onClick={() => handleSelectNote(note.id)}
                  className={`w-full text-left px-3 py-3 border-b border-[var(--border)] transition-colors ${
                    selectedNoteId === note.id
                      ? "bg-[var(--bg-subtle)] border-l-2 border-l-[var(--primary)]"
                      : "hover:bg-[var(--bg-subtle)] border-l-2 border-l-transparent"
                  }`}
                >
                  <p className="text-sm font-medium text-[var(--foreground)] truncate">
                    {note.title}
                  </p>
                  <p className="text-xs font-mono text-[var(--text-muted)] mt-0.5">
                    {note.date} · {note.author}
                  </p>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {note.tags.map((tag) => (
                      <span
                        key={tag}
                        className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${TAG_COLORS[tag]}`}
                      >
                        {TAG_LABELS[tag]}
                      </span>
                    ))}
                  </div>
                </button>
              ))
            )}
          </div>

          {/* New note button */}
          <div className="p-3 border-t border-[var(--border)]">
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-[var(--primary)] hover:text-[var(--primary)] hover:bg-blue-50 text-xs"
              onClick={handleNewNote}
            >
              + New Note
            </Button>
          </div>
        </div>

        {/* ── Right pane ── */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--bg-surface)]">
          {!selectedNote ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-[var(--text-muted)]">
              <FileEdit className="size-10 opacity-40" />
              <p className="text-sm">Select a note or create a new one</p>
            </div>
          ) : (
            <>
              {/* Header bar */}
              <div className="flex items-center gap-3 px-5 py-3 border-b border-[var(--border)] shrink-0">
                <input
                  key={selectedNote.id}
                  value={editTitle}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  disabled={isLocked}
                  className="flex-1 text-sm font-semibold bg-transparent border-none outline-none text-[var(--foreground)] placeholder:text-[var(--text-muted)] disabled:opacity-70"
                  placeholder="Note title"
                />
                <span
                  role="status"
                  className={`text-xs shrink-0 ${autoSaveColor[autoSave]}`}
                >
                  {autoSaveLabel[autoSave]}
                </span>
                <Separator orientation="vertical" className="h-4" />
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5 text-xs"
                  onClick={() => setIsLocked((prev) => !prev)}
                >
                  {isLocked ? (
                    <>
                      <Lock className="size-3.5" />
                      Locked
                    </>
                  ) : (
                    <>
                      <Unlock className="size-3.5" />
                      Sign &amp; Lock
                    </>
                  )}
                </Button>
              </div>

              {/* Toolbar */}
              {!isLocked && (
                <div className="flex items-center gap-0.5 px-4 py-1.5 border-b border-[var(--border)] shrink-0">
                  {[
                    {
                      label: "Bold",
                      icon: <Bold className="size-3.5" />,
                      action: () => editor?.chain().focus().toggleBold().run(),
                      active: editor?.isActive("bold"),
                    },
                    {
                      label: "Italic",
                      icon: <Italic className="size-3.5" />,
                      action: () => editor?.chain().focus().toggleItalic().run(),
                      active: editor?.isActive("italic"),
                    },
                    {
                      label: "H2",
                      icon: <Heading2 className="size-3.5" />,
                      action: () => editor?.chain().focus().toggleHeading({ level: 2 }).run(),
                      active: editor?.isActive("heading", { level: 2 }),
                    },
                    {
                      label: "H3",
                      icon: <Heading3 className="size-3.5" />,
                      action: () => editor?.chain().focus().toggleHeading({ level: 3 }).run(),
                      active: editor?.isActive("heading", { level: 3 }),
                    },
                    {
                      label: "Bullet list",
                      icon: <List className="size-3.5" />,
                      action: () => editor?.chain().focus().toggleBulletList().run(),
                      active: editor?.isActive("bulletList"),
                    },
                    {
                      label: "Ordered list",
                      icon: <ListOrdered className="size-3.5" />,
                      action: () => editor?.chain().focus().toggleOrderedList().run(),
                      active: editor?.isActive("orderedList"),
                    },
                  ].map(({ label, icon, action, active }) => (
                    <button
                      key={label}
                      aria-label={label}
                      onClick={action}
                      className={`p-1.5 rounded transition-colors ${
                        active
                          ? "bg-[var(--bg-subtle)] text-[var(--primary)]"
                          : "text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--foreground)]"
                      }`}
                    >
                      {icon}
                    </button>
                  ))}
                </div>
              )}

              {/* Editor */}
              <div className="flex-1 overflow-y-auto px-5 py-4">
                <EditorContent editor={editor} />
              </div>
            </>
          )}
        </div>
      </div>
    </>
  )
}
