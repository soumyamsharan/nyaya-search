import { Suspense } from "react";
import { StatuteActView } from "@/components/StatutePages";

async function ActFromParams({
  params,
  searchParams,
}: {
  params: Promise<{ key: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { key } = await params;
  const { page } = await searchParams;
  const pageNumber = Math.max(1, Math.min(1000, Number.parseInt(page ?? "1", 10) || 1));
  return <StatuteActView statuteKey={key} pageNumber={pageNumber} />;
}

export default function StatuteActPage(props: PageProps<"/statutes/[key]">) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading Act…</p>}>
      <ActFromParams params={props.params} searchParams={props.searchParams} />
    </Suspense>
  );
}
