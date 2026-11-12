"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { api } from "@/lib/api";
import type { Answer, Breakdown, CitationGraph } from "@/lib/types";
import { CitedSentences, MachineGenerated, Notice, ParagraphLink, Section, StatusMessage } from "./ui";

const BREAKDOWN_SECTIONS: { key: keyof Pick<Breakdown, "facts" | "issues" | "held" | "ratio">; title: string }[] = [
  { key: "facts", title: "Facts" },
  { key: "issues", title: "Issues" },
  { key: "held", title: "Held" },
  { key: "ratio", title: "Ratio" },
];
const MAX_QUESTION = 1000;

export function BreakdownPanel({ judgmentId }: { judgmentId: string }) {
  const [breakdown, setBreakdown] = useState<Breakdown | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setBreakdown(await api.breakdown(judgmentId));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Section title="Breakdown">
      {!breakdown && !error ? (
        <button onClick={load} disabled={loading} className="rounded-md border border-indigo-300 px-3 py-1.5 text-sm text-indigo-700 disabled:opacity-50">
          {loading ? "Preparing breakdown… (first time can take a while)" : "Show facts, issues, held and ratio"}
        </button>
      ) : null}
      {error ? <StatusMessage error={error} /> : null}
      {breakdown ? (
        <div className="space-y-4">
          {BREAKDOWN_SECTIONS.map(({ key, title }) =>
            breakdown[key].length ? (
              <div key={key}>
                <h3 className="mb-1 text-sm font-semibold">{title}</h3>
                <CitedSentences sentences={breakdown[key]} />
              </div>
            ) : null,
          )}
          <MachineGenerated />
        </div>
      ) : null}
    </Section>
  );
}

export function QuestionPanel({ judgmentId }: { judgmentId: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await api.ask(judgmentId, question.trim()));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Section title="Ask about this judgment">
      <form onSubmit={submit} className="space-y-2">
        <textarea
          value={question}
          maxLength={MAX_QUESTION}
          onChange={(e) => setQuestion(e.target.value)}
          rows={2}
          placeholder="e.g. What did the court hold on service of the demand notice?"
          className="w-full rounded-md border border-slate-300 p-2 text-sm"
        />
        <p className="text-xs text-slate-500">
          Your question is processed by an external AI model provider and is not stored by Nyaya Search.
        </p>
        <button type="submit" disabled={loading || !question.trim()} className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white disabled:opacity-50">
          {loading ? "Answering…" : "Ask"}
        </button>
      </form>
      <div className="mt-3 space-y-2">
        {error ? <StatusMessage error={error} /> : null}
        {answer && !answer.answered ? <Notice>{answer.message}</Notice> : null}
        {answer?.answered ? (
          <>
            <CitedSentences sentences={answer.sentences} />
            <MachineGenerated />
          </>
        ) : null}
      </div>
    </Section>
  );
}

function JudgmentLine({ link }: { link: CitationGraph["cites"][number] }) {
  return (
    <Link href={`/judgments/${link.judgment.id}`} className="text-indigo-700 hover:underline">
      {link.judgment.title}
      {link.judgment.citation ? `, ${link.judgment.citation}` : ""}
    </Link>
  );
}

export function CitationsPanel({ graph }: { graph: CitationGraph | null }) {
  if (!graph) return null;
  return (
    <Section title="Citations">
      <div className="space-y-4 text-sm">
        {graph.overruling_evidence.map((link) => (
          <Notice key={`${link.judgment.id}-${link.paragraph.seq}`} tone="warn">
            <p className="font-medium">
              Overruling language found in <JudgmentLine link={link} />{" "}
              <Link href={`/judgments/${link.judgment.id}#p-${link.paragraph.seq}`} className="underline">
                ¶{link.paragraph.label}
              </Link>
              . Read the citing paragraph to see what it says about this judgment.
            </p>
            {link.paragraph_text ? <p className="mt-2 text-xs">{link.paragraph_text}</p> : null}
          </Notice>
        ))}
        <div>
          <h3 className="font-semibold">Cited by ({graph.cited_by.length})</h3>
          {graph.cited_by.length ? (
            <ul className="mt-1 space-y-1">
              {graph.cited_by.map((link) => (
                <li key={`${link.judgment.id}-${link.paragraph.seq}`}>
                  <JudgmentLine link={link} />{" "}
                  <Link href={`/judgments/${link.judgment.id}#p-${link.paragraph.seq}`} className="text-xs text-slate-500 hover:underline">
                    in ¶{link.paragraph.label}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500">No judgment in the corpus cites this one yet.</p>
          )}
        </div>
        <div>
          <h3 className="font-semibold">Cites ({graph.cites.length + graph.unresolved.length})</h3>
          <ul className="mt-1 space-y-1">
            {graph.cites.map((link) => (
              <li key={link.judgment.id}>
                <JudgmentLine link={link} />
                <ParagraphLink seq={link.paragraph.seq} label={link.paragraph.label} />
              </li>
            ))}
            {graph.unresolved.map((c, i) => (
              <li key={`u-${i}`} className="text-slate-600">
                {c.raw} <span className="text-xs text-slate-400">(not in corpus)</span>
                <ParagraphLink seq={c.paragraph.seq} label={c.paragraph.label} />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  );
}
