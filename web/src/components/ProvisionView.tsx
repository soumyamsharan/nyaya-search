"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Provision, ProvisionKind } from "@/lib/types";
import { Notice, Section, StatusMessage, formatDate } from "./ui";

const KIND_LABEL: Record<ProvisionKind, string> = {
  section: "Section",
  article: "Article",
  rule: "Rule",
  regulation: "Regulation",
  notification: "Notification",
};

const EXCERPT_LENGTH = 500;

function excerpt(text: string): string {
  return text.length > EXCERPT_LENGTH ? `${text.slice(0, EXCERPT_LENGTH)}…` : text;
}

export function ProvisionView({ kind, statuteKey, slug }: { kind: ProvisionKind; statuteKey: string; slug: string }) {
  const [page, setPage] = useState<Provision | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .provision(kind, statuteKey, slug)
      .then((result) => !cancelled && setPage(result))
      .catch((e) => !cancelled && setError(e));
    return () => {
      cancelled = true;
    };
  }, [kind, statuteKey, slug]);

  if (error) return <StatusMessage error={error} />;
  if (!page) return <p className="text-sm text-slate-500">Loading provision…</p>;

  const title = `${KIND_LABEL[page.kind]} ${page.number}, ${page.name}`;
  const actHref = page.kind === "article" ? null : `/statutes/${page.key}`;

  return (
    <div className="space-y-4">
      <p className="text-sm">
        <Link href="/statutes" className="text-indigo-700 hover:underline">
          Statutes
        </Link>
        {actHref ? (
          <>
            {" / "}
            <Link href={actHref} className="text-indigo-700 hover:underline">
              {page.name}
            </Link>
          </>
        ) : null}
      </p>
      <h1 className="text-xl font-semibold">{title}</h1>

      <Section title="What it means">
        {page.description ? (
          <p className="text-sm text-slate-700">{page.description}</p>
        ) : (
          <p className="text-sm text-slate-600">
            A plain-language description of this provision is not available yet. The judgments below show how the
            Supreme Court has applied it.
          </p>
        )}
        <p className="mt-3 text-sm">
          <a
            href={page.official_url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-indigo-700 hover:underline"
          >
            Search for the official text on India Code
          </a>{" "}
          <span className="text-xs text-slate-500">(opens in a new window)</span>
        </p>
      </Section>

      <Section title={`Judgments that refer to it · ${page.judgments_total}`}>
        {page.judgments.length === 0 ? (
          <Notice>No judgment in the corpus refers to this provision.</Notice>
        ) : (
          <ol className="space-y-4">
            {page.judgments.map(({ judgment, paragraphs }) => (
              <li key={judgment.id} className="rounded-lg border border-slate-200 bg-white p-4">
                <Link href={`/judgments/${judgment.id}`} className="font-semibold text-indigo-700 hover:underline">
                  {judgment.title}
                </Link>
                <p className="mt-1 text-xs text-slate-500">
                  {[judgment.citation, formatDate(judgment.decision_date)].filter(Boolean).join(" · ")}
                </p>
                {paragraphs.slice(0, 2).map((p) => (
                  <blockquote key={p.label} className="mt-3 border-l-4 border-indigo-200 pl-3 text-sm text-slate-700">
                    <Link
                      href={`/judgments/${judgment.id}#p-${p.label}`}
                      className="mr-1 font-medium text-indigo-700 hover:underline"
                    >
                      ¶{p.label}
                    </Link>
                    {excerpt(p.text)}
                  </blockquote>
                ))}
              </li>
            ))}
          </ol>
        )}
      </Section>

      {page.related.length > 0 ? (
        <Section title="Related judgments">
          <p className="mb-3 text-xs text-slate-500">
            Judgments that discuss other provisions of this Act and are closest in meaning to this one. They do not refer
            to this provision.
          </p>
          <ol className="space-y-3">
            {page.related.map((r) => (
              <li key={`${r.judgment.id}-${r.label}`} className="rounded-lg border border-slate-200 bg-white p-4">
                <Link href={`/judgments/${r.judgment.id}`} className="font-semibold text-indigo-700 hover:underline">
                  {r.judgment.title}
                </Link>
                <p className="mt-1 text-xs text-slate-500">
                  {[r.judgment.citation, formatDate(r.judgment.decision_date)].filter(Boolean).join(" · ")}
                </p>
                <p className="mt-2 text-sm text-slate-700">
                  <Link href={`/judgments/${r.judgment.id}#p-${r.label}`} className="mr-1 font-medium text-indigo-700 hover:underline">
                    ¶{r.label}
                  </Link>
                  {excerpt(r.text)}
                </p>
              </li>
            ))}
          </ol>
        </Section>
      ) : null}
    </div>
  );
}
