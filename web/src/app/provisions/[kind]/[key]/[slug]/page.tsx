import { Suspense } from "react";
import { notFound } from "next/navigation";
import { ProvisionView } from "@/components/ProvisionView";
import { PROVISION_KINDS, type ProvisionKind } from "@/lib/types";

function isProvisionKind(value: string): value is ProvisionKind {
  return (PROVISION_KINDS as readonly string[]).includes(value);
}

async function ProvisionFromParams({ params }: { params: Promise<{ kind: string; key: string; slug: string }> }) {
  const { kind, key, slug } = await params;
  if (!isProvisionKind(kind)) notFound();
  return <ProvisionView kind={kind} statuteKey={key} slug={slug} />;
}

export default function ProvisionPage(props: PageProps<"/provisions/[kind]/[key]/[slug]">) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading provision…</p>}>
      <ProvisionFromParams params={props.params} />
    </Suspense>
  );
}
