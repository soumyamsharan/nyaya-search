// Research note: paragraphs collected in this browser only (localStorage), exported as Markdown.

export interface NoteItem {
  judgmentId: string;
  title: string;
  citation: string | null;
  label: string;
  text: string;
}

const KEY = "nyaya.researchNote.v1";
export const NOTES_CHANGED = "nyaya:notes-changed";

export function pinpointCitation(title: string, citation: string | null, label: string): string {
  return [title, citation, `¶${label}`].filter(Boolean).join(", ");
}

/** A paragraph ready to paste into a brief: its text followed by the pinpoint citation. */
export function citedParagraph(title: string, citation: string | null, label: string, text: string): string {
  return `“${text}”\n— ${pinpointCitation(title, citation, label)}`;
}

export function loadNotes(): NoteItem[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as NoteItem[]) : [];
  } catch {
    return [];
  }
}

function save(items: NoteItem[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    // storage unavailable (private mode): the note simply is not kept
  }
  window.dispatchEvent(new Event(NOTES_CHANGED));
}

const sameItem = (a: NoteItem, b: NoteItem) => a.judgmentId === b.judgmentId && a.label === b.label;

export function addNote(item: NoteItem): void {
  const items = loadNotes();
  if (!items.some((existing) => sameItem(existing, item))) save([...items, item]);
}

export function clearNotes(): void {
  save([]);
}

export function notesToMarkdown(items: NoteItem[]): string {
  const byJudgment = new Map<string, NoteItem[]>();
  items.forEach((item) => byJudgment.set(item.judgmentId, [...(byJudgment.get(item.judgmentId) ?? []), item]));
  const sections = [...byJudgment.values()].map((group) => {
    const { title, citation } = group[0];
    const paragraphs = group.map((p) => `**¶${p.label}** — ${p.text}`).join("\n\n");
    return `## ${title}${citation ? `, ${citation}` : ""}\n\n${paragraphs}`;
  });
  return `# Research note\n\n${sections.join("\n\n")}\n\n---\nSource: Nyaya Search. Read each judgment before citing it.\n`;
}

export function downloadMarkdown(filename: string, markdown: string): void {
  const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
