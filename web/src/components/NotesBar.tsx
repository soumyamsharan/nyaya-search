"use client";

import { useEffect, useState } from "react";
import { NOTES_CHANGED, type NoteItem, clearNotes, downloadMarkdown, loadNotes, notesToMarkdown } from "@/lib/notes";

export default function NotesBar() {
  const [items, setItems] = useState<NoteItem[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () => setItems(loadNotes());
    refresh();
    window.addEventListener(NOTES_CHANGED, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(NOTES_CHANGED, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  function exportNote() {
    if (!items.length) {
      setMessage("Your research note is empty. Use “Add to note” on any paragraph first.");
      return;
    }
    setMessage(null);
    downloadMarkdown("research-note.md", notesToMarkdown(items));
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <span className="text-slate-600">Research note: {items.length} paragraph{items.length === 1 ? "" : "s"}</span>
      <button onClick={exportNote} className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50">
        Export Markdown
      </button>
      {items.length ? (
        <button onClick={clearNotes} className="text-slate-500 hover:underline">
          Clear
        </button>
      ) : null}
      {message ? <span className="text-amber-700">{message}</span> : null}
    </div>
  );
}
