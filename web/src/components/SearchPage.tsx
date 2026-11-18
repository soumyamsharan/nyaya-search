"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { MATCH_IN } from "@/lib/roles";
import type { SearchFilters, SearchResponse, StatuteSummary } from "@/lib/types";
import Combobox, { type Option } from "./Combobox";
import DateField from "./DateField";
import { Notice, ResultSkeleton, Spinner, StatusMessage, formatDate } from "./ui";

type FieldKind = "date" | "judges" | "author" | "outcome" | "match" | "act" | "section";
interface FilterField {
  key: keyof SearchFilters;
  label: string;
  kind: FieldKind;
}

const OUTCOMES = [
  { value: "", label: "Any outcome" },
  { value: "allowed", label: "Allowed" },
  { value: "partly_allowed", label: "Partly allowed" },
  { value: "dismissed", label: "Dismissed" },
  { value: "disposed", label: "Disposed of" },
  { value: "other", label: "Other / not recorded" },
];

const FILTER_FIELDS: FilterField[] = [
  { key: "date_from", label: "Decided from", kind: "date" },
  { key: "date_to", label: "Decided to", kind: "date" },
  { key: "judge", label: "Judges on bench", kind: "judges" },
  { key: "author", label: "Judgment written by", kind: "author" },
  { key: "outcome", label: "Outcome", kind: "outcome" },
  { key: "match_in", label: "Match in", kind: "match" },
  { key: "act", label: "Act", kind: "act" },
  { key: "section", label: "Section", kind: "section" },
];
const URL_ONLY_FILTERS: (keyof SearchFilters)[] = ["year_from", "year_to"]; // older links keep working
const MAX_QUERY = 2000;
const EXAMPLE = "Cheque dishonoured, demand notice sent but never received; is the Section 138 complaint maintainable?";

interface SearchOutcome {
  key: string; // the URL query this outcome belongs to
  response?: SearchResponse;
  error?: unknown;
}

function readFilters(params: URLSearchParams): SearchFilters {
  const keys = [...FILTER_FIELDS.map((f) => f.key), ...URL_ONLY_FILTERS];
  return Object.fromEntries(keys.map((key) => [key, params.get(key) ?? ""])) as SearchFilters;
}

export default function SearchPage() {
  const router = useRouter();
  const params = useSearchParams();
  const urlQuery = params.get("q") ?? "";
  const [query, setQuery] = useState(urlQuery);
  const [filters, setFilters] = useState<SearchFilters>(() => readFilters(params));
  const [outcome, setOutcome] = useState<SearchOutcome>({ key: "" });
  const [hint, setHint] = useState<string | null>(null);
  const [judges, setJudges] = useState<Option[]>([]);
  const [acts, setActs] = useState<StatuteSummary[]>([]);
  const key = params.toString();
  const activeFilters = FILTER_FIELDS.filter((f) => params.get(f.key)).length;

  useEffect(() => {
    api
      .judges()
      .then((list) => setJudges(list.map((j) => ({ value: j.name, label: j.name, hint: `${j.judgments}` }))))
      .catch(() => setJudges([]));
    api.statutes().then((index) => setActs(index.acts)).catch(() => setActs([]));
  }, []);

  // Section choices come from the Act chosen in the Act field.
  const actName = (filters.act ?? "").trim().toLowerCase();
  const chosenAct = acts.find((a) => a.name.toLowerCase() === actName);
  const actOptions: Option[] = acts.map((a) => ({
    value: a.name,
    label: a.name,
    hint: `${a.judgments}`,
    keywords: a.key.replace(/-/g, " "), // so "negotiable" finds "NI Act"
  }));
  const sectionOptions: Option[] = (chosenAct?.sections ?? []).map((s) => ({
    value: s.section,
    label: `Section ${s.section}`,
    hint: `${s.judgments}`,
  }));

  /** Run another query with the current URL filters (used by "Did you mean"). */
  function searchFor(text: string) {
    const next = new URLSearchParams(params);
    next.set("q", text);
    setQuery(text);
    router.push(`/?${next}`);
  }

  useEffect(() => {
    if (!urlQuery.trim()) return;
    let cancelled = false;
    api
      .search(urlQuery, readFilters(new URLSearchParams(key)))
      .then((response) => !cancelled && setOutcome({ key, response }))
      .catch((error) => !cancelled && setOutcome({ key, error }));
    return () => {
      cancelled = true;
    };
  }, [urlQuery, key]);

  const loading = Boolean(urlQuery.trim()) && outcome.key !== key;
  const current = outcome.key === key ? outcome : { key };
  const { response, error } = current;

  function renderFilter({ key: field, label, kind }: FilterField) {
    const id = `filter-${field}`;
    const value = filters[field] ?? "";
    const set = (next: string) => setFilters((f) => ({ ...f, [field]: next }));
    const judgeNames = { emptyText: "No judge matches", placeholder: "Type a name" };
    switch (kind) {
      case "date":
        return <DateField id={id} label={label} value={value} onChange={set} />;
      case "judges":
        return <Combobox id={id} label={label} value={value} onChange={set} options={judges} multi freeText {...judgeNames} />;
      case "author":
        return <Combobox id={id} label={label} value={value} onChange={set} options={judges} freeText {...judgeNames} />;
      case "outcome":
        return <Combobox id={id} label={label} value={value} onChange={set} options={OUTCOMES} placeholder="Any outcome" />;
      case "match":
        return <Combobox id={id} label={label} value={value} onChange={set} options={MATCH_IN} placeholder="Anywhere in the judgment" />;
      case "act":
        return (
          <Combobox
            id={id}
            label={label}
            value={value}
            onChange={set}
            options={actOptions}
            freeText
            placeholder="Type an Act, e.g. Negotiable"
            emptyText="No Act matches"
          />
        );
      case "section":
        return (
          <Combobox
            id={id}
            label={label}
            value={value}
            onChange={set}
            options={sectionOptions}
            freeText
            placeholder={chosenAct ? "Type a section number" : "Choose an Act first"}
            emptyText={chosenAct ? "No section matches" : "Choose an Act to see its sections"}
          />
        );
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) {
      setHint("Describe the facts, a quoted phrase or a citation.");
      return;
    }
    setHint(null);
    const next = new URLSearchParams({ q: query.trim() });
    Object.entries(filters).forEach(([key, value]) => value && next.set(key, value));
    router.push(`/?${next}`);
  }

  return (
    <div className="space-y-6">
      <form onSubmit={submit} className="space-y-3">
        <label htmlFor="q" className="block text-sm font-medium text-ink-soft">
          Describe the facts and the legal issue, quote a phrase, or paste a citation
        </label>
        <textarea
          id="q"
          value={query}
          maxLength={MAX_QUERY}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          placeholder={EXAMPLE}
          className="w-full rounded-md border border-rule p-3 text-sm focus:border-accent focus:outline-none"
        />
        <p className="text-xs text-muted">
          Tip: <code>AND</code> requires both words, <code>OR</code> allows either, <code>NOT</code> excludes a word or
          &quot;quoted phrase&quot; (operators in capitals), e.g. <code>bail NOT anticipatory</code>.
        </p>
        <details open={activeFilters > 0} className="group rounded-md border border-rule bg-surface">
          <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm text-ink-soft hover:text-ink">
            <span>
              Refine search
              {activeFilters ? <span className="ml-2 text-accent">{activeFilters} set</span> : null}
            </span>
            <span className="text-muted transition-transform group-open:rotate-180" aria-hidden>
              ▾
            </span>
          </summary>
          <div className="grid grid-cols-2 items-start gap-x-4 gap-y-5 border-t border-rule px-4 py-5 sm:grid-cols-4">
            {FILTER_FIELDS.map((field) => (
              <div key={field.key} className="min-w-0">
                {renderFilter(field)}
              </div>
            ))}
          </div>
        </details>
        <button type="submit" disabled={loading} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
          {loading ? (
            <>
              <Spinner className="mr-1.5" />
              Searching…
            </>
          ) : (
            "Search"
          )}
        </button>
      </form>

      {hint ? <Notice>{hint}</Notice> : null}
      {response?.suggestion && !error ? (
        <p className="text-sm text-ink-soft">
          Did you mean:{" "}
          <button type="button" onClick={() => searchFor(response.suggestion!)} className="font-medium text-accent underline">
            {response.suggestion}
          </button>
          ?
        </p>
      ) : null}
      {error ? <StatusMessage error={error} /> : null}
      {response?.message && !error ? <Notice>{response.message}</Notice> : null}

      {loading && !response ? <ResultSkeleton /> : null}
      <ol className="divide-y divide-rule border-y border-rule">
        {response?.results.map(({ judgment, matched_paragraph: p }, index) => (
          <li key={judgment.id} className="flex gap-4 py-6">
            <span className="w-6 shrink-0 pt-1 font-serif text-sm tabular-nums text-muted">{index + 1}</span>
            <div className="min-w-0 flex-1">
              <Link
                href={`/judgments/${judgment.id}`}
                onMouseEnter={() => api.prefetchJudgment(judgment.id)}
                onFocus={() => api.prefetchJudgment(judgment.id)}
                className="font-serif text-xl leading-snug text-ink underline decoration-accent/60 decoration-1 underline-offset-[5px] hover:text-accent hover:decoration-accent"
              >
                {judgment.title}
              </Link>
              <p className="mt-1 text-xs text-muted">
                {[judgment.citation, formatDate(judgment.decision_date), judgment.bench.join(", ")].filter(Boolean).join(" · ")}
                {" · "}Cited by {judgment.cited_by_count} in corpus
              </p>
              <blockquote className="reading mt-3 border-l-2 border-accent pl-4 text-[0.95rem] text-ink-soft">
                <Link href={`/judgments/${judgment.id}#p-${p.seq}`} className="mr-1.5 font-sans text-xs font-medium text-accent hover:underline">
                  ¶{p.label}
                </Link>
                {p.text.length > 600 ? `${p.text.slice(0, 600)}…` : p.text}
              </blockquote>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
