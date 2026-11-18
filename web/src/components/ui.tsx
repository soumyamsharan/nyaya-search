"use client";

import type { ReactNode } from "react";
import { ApiError } from "@/lib/api";
import type { CitedSentence } from "@/lib/types";

const TONES = {
  info: "border-rule bg-paper text-ink-soft",
  warn: "border-amber-300 bg-amber-50 text-amber-900",
  error: "border-red-300 bg-red-50 text-red-800",
};

export function Notice({ tone = "info", children }: { tone?: keyof typeof TONES; children: ReactNode }) {
  return <div className={`rounded-md border px-4 py-3 text-sm ${TONES[tone]}`}>{children}</div>;
}

const ERROR_TEXT: Partial<Record<ApiError["kind"], string>> = {
  unreachable: "The service is waking up or temporarily unavailable. Please try again in a minute or two.",
  busy: "AI answers are busy right now. Please try again in a minute — search and reading still work.",
  unavailable: "This AI feature is temporarily unavailable. The judgment text below is unaffected.",
  rate_limited: "Too many requests. Please wait a minute and try again.",
};

/** One place that turns any API failure into a friendly message. */
export function StatusMessage({ error }: { error: unknown }) {
  const apiError = error instanceof ApiError ? error : null;
  const text = (apiError && ERROR_TEXT[apiError.kind]) ?? apiError?.message ?? "Something went wrong.";
  const tone = apiError?.kind === "busy" || apiError?.kind === "unavailable" ? "warn" : "error";
  return <Notice tone={tone}>{text}</Notice>;
}

export function MachineGenerated() {
  return (
    <p className="text-xs text-muted">
      Machine-generated from the judgment&apos;s own paragraphs. A research aid only — read the judgment before
      citing it.
    </p>
  );
}

export function ParagraphLink({ seq, label }: { seq: number; label: string }) {
  return (
    <a href={`#p-${seq}`} className="ml-1 rounded bg-accent-soft px-1 text-xs font-medium text-accent hover:underline">
      ¶{label}
    </a>
  );
}

/** Generated sentences, each followed by links to the paragraphs that support it. Rendered as text only. */
export function CitedSentences({ sentences }: { sentences: CitedSentence[] }) {
  return (
    <ul className="space-y-1.5">
      {sentences.map((sentence, i) => (
        <li key={i} className="text-sm leading-relaxed">
          {sentence.text}
          {sentence.paragraphs.map((p) => (
            <ParagraphLink key={p.seq} seq={p.seq} label={p.label} />
          ))}
        </li>
      ))}
    </ul>
  );
}

export function Section({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="rounded-md border border-rule bg-surface p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-serif text-lg font-medium text-ink">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function formatDate(value: string | null): string {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

/** A small spinner for buttons that are waiting on a request. Hidden from screen readers; the button label says it. */
export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg className={`inline-block size-3.5 animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/** A grey placeholder bar that pulses while content loads. */
export function Bar({ width = "100%", height = "0.75rem" }: { width?: string; height?: string }) {
  return <div className="animate-pulse rounded bg-rule/70" style={{ width, height }} />;
}

/** Placeholder rows shaped like search results, shown while a search runs. */
export function ResultSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading results" className="divide-y divide-rule border-y border-rule">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex gap-4 py-6">
          <div className="w-6 shrink-0" />
          <div className="flex-1 space-y-3">
            <Bar width="70%" height="1.25rem" />
            <Bar width="45%" />
            <Bar width="100%" height="4.5rem" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Placeholder shaped like a judgment page: title, metadata and a few paragraphs. */
export function JudgmentSkeleton() {
  return (
    <div role="status" aria-label="Loading judgment" className="space-y-6">
      <div className="space-y-3">
        <Bar width="80%" height="1.75rem" />
        <Bar width="55%" />
        <Bar width="35%" />
      </div>
      <div className="space-y-5">
        {[0, 1, 2].map((i) => (
          <div key={i} className="space-y-2.5">
            <Bar width="100%" />
            <Bar width="92%" />
            <Bar width="60%" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Placeholder lines for a list page (statutes, Acts, provisions). */
export function ListSkeleton({ label, rows = 6 }: { label: string; rows?: number }) {
  return (
    <div role="status" aria-label={label} className="space-y-4">
      {Array.from({ length: rows }, (_, i) => (
        <Bar key={i} width={`${65 + ((i * 17) % 30)}%`} height="1rem" />
      ))}
    </div>
  );
}
