import { Suspense } from "react";
import JudgmentView from "@/components/JudgmentView";
import { JudgmentSkeleton } from "@/components/ui";

async function JudgmentFromParams({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <JudgmentView id={id} />;
}

export default function JudgmentPage(props: PageProps<"/judgments/[id]">) {
  return (
    <Suspense fallback={<JudgmentSkeleton />}>
      <JudgmentFromParams params={props.params} />
    </Suspense>
  );
}
