"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { StatuteActPage, StatuteIndex, StatuteSectionPage } from "@/lib/types";
import { Notice, Section, StatusMessage, formatDate } from "./ui";

export function StatuteIndexView() {
  const [index, setIndex] = useState<StatuteIndex | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.statutes().then(setIndex).catch(setError);
  }, []);

  if (error) return <StatusMessage error={error} />;
  if (!index) return <p className="text-sm text-slate-500">Loading statutes…</p>;
  const term = query.trim().toLowerCase();
  const acts = index.acts.filter((a) => !term || a.name.toLowerCase().includes(term));
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Statutes</h1>
      <p className="text-sm text-slate-600">
        Acts and sections that the Supreme Court judgments in the corpus refer to. Choose a section to see the judgments
        that interpret it, with the paragraph where each does so.
      </p>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Filter Acts, e.g. Negotiable"
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
      />
      {acts.length === 0 ? <Notice>No Act matches “{query}”.</Notice> : null}
      <ul className="space-y-3">
        {acts.map((act) => (
          <li key={act.key}>
            <Section title={`${act.name} · ${act.judgments} judgments`}>
              <Link href={`/statutes/${act.key}`} className="mb-2 inline-block text-xs font-medium text-indigo-700 hover:underline">
                All judgments under this Act →
              </Link>
              <div className="flex flex-wrap gap-1.5">
                {act.sections.slice(0, 40).map((s) => (
                  <Link
                    key={s.section}
                    href={`/statutes/${act.key}/sections/${s.section}`}
                    className="rounded-full border border-slate-300 px-2.5 py-0.5 text-xs text-indigo-700 hover:bg-indigo-50"
                  >
                    s. {s.section} ({s.judgments})
                  </Link>
                ))}
              </div>
            </Section>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function StatuteSectionView({ statuteKey, section }: { statuteKey: string; section: string }) {
  const [page, setPage] = useState<StatuteSectionPage | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.statuteSection(statuteKey, section).then(setPage).catch(setError);
  }, [statuteKey, section]);

  if (error) return <StatusMessage error={error} />;
  if (!page) return <p className="text-sm text-slate-500">Loading section…</p>;
  return (
    <div className="space-y-4">
      <p className="text-sm">
        <Link href="/statutes" className="text-indigo-700 hover:underline">
          Statutes
        </Link>{" "}
        /{" "}
        <Link href={`/statutes/${page.key}`} className="text-indigo-700 hover:underline">
          {page.name}
        </Link>
      </p>
      <h1 className="text-xl font-semibold">Section {page.section}, {page.name}</h1>
      <p className="text-sm text-slate-600">
        {page.judgments.length} judgment{page.judgments.length === 1 ? "" : "s"} refer to this section. The paragraph
        shown is where each judgment refers to it.
      </p>
      <ol className="space-y-4">
        {page.judgments.map(({ judgment, paragraphs }) => (
          <li key={judgment.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <Link href={`/judgments/${judgment.id}`} className="font-semibold text-indigo-700 hover:underline">
              {judgment.title}
            </Link>
            <p className="mt-1 text-xs text-slate-500">
              {[judgment.citation, formatDate(judgment.decision_date)].filter(Boolean).join(" · ")}
            </p>
            {paragraphs.slice(0, 3).map((p) => (
              <blockquote key={p.label} className="mt-3 border-l-4 border-indigo-200 pl-3 text-sm text-slate-700">
                <Link href={`/judgments/${judgment.id}#p-${p.label}`} className="mr-1 font-medium text-indigo-700 hover:underline">
                  ¶{p.label}
                </Link>
                {p.text.length > 500 ? `${p.text.slice(0, 500)}…` : p.text}
              </blockquote>
            ))}
          </li>
        ))}
      </ol>
    </div>
  );
}

export function StatuteActView({ statuteKey, pageNumber }: { statuteKey: string; pageNumber: number }) {
  const [data, setData] = useState<StatuteActPage | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .statuteAct(statuteKey, pageNumber)
      .then((page) => !cancelled && setData(page))
      .catch((e) => !cancelled && setError(e));
    return () => {
      cancelled = true;
    };
  }, [statuteKey, pageNumber]);

  if (error) return <StatusMessage error={error} />;
  if (!data) return <p className="text-sm text-slate-500">Loading Act…</p>;
  const pages = Math.ceil(data.judgments_total / data.per_page);
  return (
    <div className="space-y-4">
      <p className="text-sm">
        <Link href="/statutes" className="text-indigo-700 hover:underline">
          Statutes
        </Link>{" "}
        / {data.name}
      </p>
      <h1 className="text-xl font-semibold">{data.name}</h1>
      <p className="text-sm text-slate-600">
        {data.judgments_total} judgments refer to this Act, in any section. Newest first.
      </p>
      <ol className="space-y-3">
        {data.judgments.map(({ judgment, sections }) => (
          <li key={judgment.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <Link href={`/judgments/${judgment.id}`} className="font-semibold text-indigo-700 hover:underline">
              {judgment.title}
            </Link>
            <p className="mt-1 text-xs text-slate-500">
              {[judgment.citation, formatDate(judgment.decision_date)].filter(Boolean).join(" · ")}
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {sections.map((s) => (
                <Link
                  key={s}
                  href={`/statutes/${data.key}/sections/${s}`}
                  className="rounded-full border border-slate-300 px-2 py-0.5 text-xs text-indigo-700 hover:bg-indigo-50"
                >
                  s. {s}
                </Link>
              ))}
            </div>
          </li>
        ))}
      </ol>
      {pages > 1 ? (
        <nav className="flex items-center justify-between text-sm">
          {pageNumber > 1 ? (
            <Link href={`/statutes/${data.key}?page=${pageNumber - 1}`} className="text-indigo-700 hover:underline">
              ← Newer
            </Link>
          ) : (
            <span />
          )}
          <span className="text-slate-500">
            Page {pageNumber} of {pages}
          </span>
          {pageNumber < pages ? (
            <Link href={`/statutes/${data.key}?page=${pageNumber + 1}`} className="text-indigo-700 hover:underline">
              Older →
            </Link>
          ) : (
            <span />
          )}
        </nav>
      ) : null}
    </div>
  );
}
