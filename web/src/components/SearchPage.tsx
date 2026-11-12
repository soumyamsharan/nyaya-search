"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { MATCH_IN } from "@/lib/roles";
import type { SearchFilters, SearchResponse } from "@/lib/types";
import { Notice, StatusMessage, formatDate } from "./ui";

type Field =
  | { key: keyof SearchFilters; label: string; type: "text" | "date"; placeholder?: string }
  | { key: keyof SearchFilters; label: string; type: "select"; options: { value: string; label: string }[] };

const OUTCOMES = [
  { value: "", label: "Any outcome" },
  { value: "allowed", label: "Allowed" },
  { value: "partly_allowed", label: "Partly allowed" },
  { value: "dismissed", label: "Dismissed" },
  { value: "disposed", label: "Disposed of" },
  { value: "other", label: "Other / not recorded" },
];

const FILTER_FIELDS: Field[] = [
  { key: "date_from", label: "Decided from", type: "date" },
  { key: "date_to", label: "Decided to", type: "date" },
  { key: "judge", label: "Judges on bench (comma-separated)", type: "text", placeholder: "e.g. Pardiwala, Mahadevan" },
  { key: "author", label: "Judgment written by", type: "text", placeholder: "e.g. Oka" },
  { key: "outcome", label: "Outcome", type: "select", options: OUTCOMES },
  { key: "match_in", label: "Match in", type: "select", options: MATCH_IN },
  { key: "act", label: "Act", type: "text", placeholder: "e.g. Negotiable Instruments Act" },
  { key: "section", label: "Section", type: "text", placeholder: "e.g. 138" },
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
  const key = params.toString();

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
        <label htmlFor="q" className="block text-sm font-medium text-slate-700">
          Describe the facts and the legal issue, quote a phrase, or paste a citation
        </label>
        <textarea
          id="q"
          value={query}
          maxLength={MAX_QUERY}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          placeholder={EXAMPLE}
          className="w-full rounded-md border border-slate-300 p-3 text-sm focus:border-indigo-500 focus:outline-none"
        />
        <p className="text-xs text-slate-500">
          Tip: <code>AND</code> requires both words, <code>OR</code> allows either, <code>NOT</code> excludes a word or
          &quot;quoted phrase&quot; (operators in capitals), e.g. <code>bail NOT anticipatory</code>.
        </p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {FILTER_FIELDS.map((field) => {
            const common = {
              value: filters[field.key] ?? "",
              onChange: (e: { target: { value: string } }) => setFilters({ ...filters, [field.key]: e.target.value }),
              className: "mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1 text-sm",
            };
            return (
              <label key={field.key} className="text-xs text-slate-600">
                {field.label}
                {field.type === "select" ? (
                  <select {...common}>
                    {field.options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input {...common} type={field.type} placeholder={field.type === "text" ? field.placeholder : undefined} />
                )}
              </label>
            );
          })}
        </div>
        <button type="submit" disabled={loading} className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {hint ? <Notice>{hint}</Notice> : null}
      {error ? <StatusMessage error={error} /> : null}
      {response?.message && !error ? <Notice>{response.message}</Notice> : null}

      <ol className="space-y-4">
        {response?.results.map(({ judgment, matched_paragraph: p }) => (
          <li key={judgment.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <Link href={`/judgments/${judgment.id}`} className="font-semibold text-indigo-700 hover:underline">
              {judgment.title}
            </Link>
            <p className="mt-1 text-xs text-slate-500">
              {[judgment.citation, formatDate(judgment.decision_date), judgment.bench.join(", ")].filter(Boolean).join(" · ")}
              {" · "}Cited by {judgment.cited_by_count} in corpus
            </p>
            <blockquote className="mt-3 border-l-4 border-indigo-200 pl-3 text-sm text-slate-700">
              <Link href={`/judgments/${judgment.id}#p-${p.seq}`} className="mr-1 font-medium text-indigo-700 hover:underline">
                ¶{p.label}
              </Link>
              {p.text.length > 600 ? `${p.text.slice(0, 600)}…` : p.text}
            </blockquote>
          </li>
        ))}
      </ol>
    </div>
  );
}
