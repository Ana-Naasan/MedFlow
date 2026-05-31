import { NotebookPen } from "lucide-react";

import { ComingSoon } from "../../../../../components/layout/ComingSoon";

export default function NotesTab() {
  return (
    <ComingSoon
      icon={NotebookPen}
      title="Notes"
      description="Tiptap editor with sign-and-lock. Will live in this tab once the notes persistence layer is added — for now use the packet tab for clinical context."
    />
  );
}
