import { Suspense } from "react";
import SharedNoteView from "@/components/SharedNoteView";

async function NoteFromParams({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SharedNoteView id={id} />;
}

export default function NotePage(props: PageProps<"/notes/[id]">) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading note…</p>}>
      <NoteFromParams params={props.params} />
    </Suspense>
  );
}
