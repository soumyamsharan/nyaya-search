import { Suspense } from "react";
import JudgmentView from "@/components/JudgmentView";

async function JudgmentFromParams({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <JudgmentView id={id} />;
}

export default function JudgmentPage(props: PageProps<"/judgments/[id]">) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading judgment…</p>}>
      <JudgmentFromParams params={props.params} />
    </Suspense>
  );
}
