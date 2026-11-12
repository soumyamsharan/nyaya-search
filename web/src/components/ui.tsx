"use client";

import type { ReactNode } from "react";
import { ApiError } from "@/lib/api";
import type { CitedSentence } from "@/lib/types";

const TONES = {
  info: "border-slate-300 bg-slate-50 text-slate-700",
  warn: "border-amber-300 bg-amber-50 text-amber-900",
  error: "border-red-300 bg-red-50 text-red-800",
};

export function Notice({ tone = "info", children }: { tone?: keyof typeof TONES; children: ReactNode }) {
  return <div className={`rounded-md border px-4 py-3 text-sm ${TONES[tone]}`}>{children}</div>;
}

const ERROR_TEXT: Partial<Record<ApiError["kind"], string>> = {
  unreachable: "The service is waking up or temporarily unavailable. Please try again in a minute or two.",
  busy: "AI features are busy right now. Please try again later — search and reading still work.",
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
    <p className="text-xs text-slate-500">
      Machine-generated from the judgment&apos;s own paragraphs. A research aid only — read the judgment before
      citing it.
    </p>
  );
}

export function ParagraphLink({ seq, label }: { seq: number; label: string }) {
  return (
    <a href={`#p-${seq}`} className="ml-1 rounded bg-indigo-50 px-1 text-xs font-medium text-indigo-700 hover:underline">
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
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">{title}</h2>
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
