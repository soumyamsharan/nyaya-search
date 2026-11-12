import { Suspense } from "react";
import { StatuteSectionView } from "@/components/StatutePages";

async function SectionFromParams({ params }: { params: Promise<{ key: string; section: string }> }) {
  const { key, section } = await params;
  return <StatuteSectionView statuteKey={key} section={section} />;
}

export default function StatuteSectionPage(props: PageProps<"/statutes/[key]/sections/[section]">) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading section…</p>}>
      <SectionFromParams params={props.params} />
    </Suspense>
  );
}
