"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type MouseEvent, type ReactNode, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { api } from "@/lib/api";
import { ROLES, type Role, parseRoles, roleInfo } from "@/lib/roles";
import { addNote, citedParagraph } from "@/lib/notes";
import type { CitationGraph, CitationRef, Judgment, Paragraph, StatuteRef } from "@/lib/types";
import { BreakdownPanel, CitationsPanel, QuestionPanel } from "./JudgmentPanels";
import { Notice, Section, StatusMessage, formatDate } from "./ui";

const PARA_REF = /\[Paras?\.?\s*([^\]]+)\]/gi;

/** The URL hash (e.g. "#p-15"), kept in sync on navigation. CSS :target misses paragraphs rendered later. */
function useHash(): string {
  return useSyncExternalStore(
    (onChange) => {
      window.addEventListener("hashchange", onChange);
      return () => window.removeEventListener("hashchange", onChange);
    },
    () => window.location.hash,
    () => "",
  );
}

/** Turn the reporter's "[Para 27]" / "[Paras 21-23]" references into links to those paragraphs. */
function linkParagraphRefs(text: string, seqByLabel: Map<string, number>): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(PARA_REF)) {
    nodes.push(text.slice(last, match.index));
    const first = match[1].match(/\d+/)?.[0];
    const seq = first ? seqByLabel.get(first) : undefined;
    nodes.push(
      seq ? (
        <a key={match.index} href={`#p-${seq}`} className="text-indigo-700 hover:underline">
          {match[0]}
        </a>
      ) : (
        match[0]
      ),
    );
    last = (match.index ?? 0) + match[0].length;
  }
  nodes.push(text.slice(last));
  return nodes;
}

function RoleTag({ role }: { role: Role | null }) {
  const info = roleInfo(role);
  return info ? (
    <span className={`mb-0.5 inline-block rounded px-1.5 text-[11px] font-medium ${info.tone}`}>{info.label}</span>
  ) : null;
}

/** The "Cites cases" toggle lives in the URL too (?cites=1), and combines with the role chips. */
function useCitesFilter(): [boolean, (on: boolean) => void] {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const on = params.get("cites") === "1";
  const set = (value: boolean) => {
    const query = new URLSearchParams(params);
    if (value) query.set("cites", "1");
    else query.delete("cites");
    router.replace(`${pathname}${query.size ? `?${query}` : ""}${window.location.hash}`, { scroll: false });
  };
  return [on, set];
}

/** One highlighted span inside a paragraph: a case citation, or a section of an Act. */
interface Span {
  raw: string;
  href: string | null;
  title: string;
  tone: string;
}

/**
 * Paragraph text with each citation and statute section highlighted: a link when the target is in the corpus,
 * otherwise a hint. Matches the text as printed, in order.
 */
function AnnotatedText({
  text,
  references,
  statutes,
}: {
  text: string;
  references: CitationRef[];
  statutes: StatuteRef[];
}) {
  const spans: Span[] = [
    ...references.map((ref) => ({
      raw: ref.raw,
      href: ref.judgment_id ? `/judgments/${ref.judgment_id}` : null,
      title: ref.judgment_id
        ? `${ref.title ?? ""}${ref.citation ? `, ${ref.citation}` : ""}`
        : "This case is not in the Nyaya Search corpus",
      tone: ref.judgment_id
        ? "rounded bg-yellow-100 px-0.5 text-indigo-800 underline decoration-dotted hover:bg-yellow-200"
        : "rounded bg-slate-100 px-0.5 text-slate-600",
    })),
    ...statutes.map((st) => ({
      raw: st.raw,
      href: `/provisions/${st.kind}/${st.key}/${st.slug}`,
      title: `Judgments that refer to ${st.raw}, and what it means`,
      tone: "rounded bg-emerald-50 px-0.5 text-emerald-800 underline decoration-dotted hover:bg-emerald-100",
    })),
  ];
  if (!spans.length) return <>{text}</>;
  const nodes: ReactNode[] = [];
  let rest = text;
  let key = 0;
  for (const span of spans) {
    const at = rest.indexOf(span.raw);
    if (at < 0) continue;
    nodes.push(rest.slice(0, at));
    nodes.push(
      span.href ? (
        <Link key={key++} href={span.href} title={span.title} className={span.tone}>
          {span.raw}
        </Link>
      ) : (
        <span key={key++} title={span.title} className={span.tone}>
          {span.raw}
        </span>
      ),
    );
    rest = rest.slice(at + span.raw.length);
  }
  nodes.push(rest);
  return <>{nodes}</>;
}

/** Role chips that filter the paragraph list; the selection lives in the URL (?roles=a,b) so it can be shared. */
function useRoleFilter(): [Role[], (role: Role | null) => void] {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const selected = parseRoles(params.get("roles"));
  const toggle = (role: Role | null) => {
    const next = role === null ? [] : selected.includes(role) ? selected.filter((r) => r !== role) : [...selected, role];
    const query = new URLSearchParams(params);
    if (next.length) query.set("roles", next.join(","));
    else query.delete("roles");
    router.replace(`${pathname}${query.size ? `?${query}` : ""}${window.location.hash}`, { scroll: false });
  };
  return [selected, toggle];
}

function RoleFilter({ selected, onToggle, counts }: { selected: Role[]; onToggle: (r: Role | null) => void; counts: Map<Role, number> }) {
  const chip = "rounded-full border px-2.5 py-0.5 text-xs";
  return (
    <div className="mb-3 space-y-1">
      <div className="flex flex-wrap gap-1.5">
        <button onClick={() => onToggle(null)} className={`${chip} ${selected.length ? "border-slate-300" : "border-indigo-500 bg-indigo-50 text-indigo-700"}`}>
          Show all
        </button>
        {ROLES.filter(({ role }) => counts.get(role)).map(({ role, label }) => (
          <button
            key={role}
            onClick={() => onToggle(role)}
            aria-pressed={selected.includes(role)}
            className={`${chip} ${selected.includes(role) ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-slate-300 text-slate-600"}`}
          >
            {label} ({counts.get(role)})
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-500">Paragraph roles are assigned automatically and may be wrong.</p>
    </div>
  );
}

function ParagraphItem({ judgment, paragraph, highlighted }: { judgment: Judgment; paragraph: Paragraph; highlighted: boolean }) {
  const [copied, setCopied] = useState(false);
  const citation = citedParagraph(judgment.title, judgment.citation, paragraph.label, paragraph.text);

  async function copy() {
    try {
      await navigator.clipboard.writeText(citation);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard not permitted; nothing else to do
    }
  }

  return (
    <li id={`p-${paragraph.seq}`} className={`group scroll-mt-20 rounded px-2 py-1 ${highlighted ? "bg-yellow-100" : ""}`}>
      <div className="flex gap-3">
        <a href={`#p-${paragraph.seq}`} className="w-12 shrink-0 pt-0.5 text-right text-xs font-semibold text-slate-400">
          ¶{paragraph.label}
        </a>
        <div className="flex-1">
          <RoleTag role={paragraph.role} />
          <p className="text-sm leading-relaxed text-slate-800">
            <AnnotatedText
              text={paragraph.text}
              references={paragraph.references ?? []}
              statutes={paragraph.statutes ?? []}
            />
          </p>
        </div>
      </div>
      <div className="ml-15 mt-1 flex gap-3 text-xs text-indigo-700 opacity-60 group-hover:opacity-100">
        <button onClick={copy}>{copied ? "Copied" : "Copy with citation"}</button>
        <button
          onClick={() =>
            addNote({ judgmentId: judgment.id, title: judgment.title, citation: judgment.citation, label: paragraph.label, text: paragraph.text })
          }
        >
          Add to note
        </button>
      </div>
    </li>
  );
}

function visibleParagraphs(paragraphs: Paragraph[], roles: Role[], citesOnly: boolean): Paragraph[] {
  return paragraphs.filter(
    (p) =>
      (!roles.length || (p.role !== null && roles.includes(p.role))) && (!citesOnly || p.cites_cases),
  );
}

function roleCounts(paragraphs: Paragraph[]): Map<Role, number> {
  const counts = new Map<Role, number>();
  paragraphs.forEach((p) => p.role && counts.set(p.role, (counts.get(p.role) ?? 0) + 1));
  return counts;
}

/**
 * In-page ¶ links jump down the page and add a history entry, but Next.js turns off the browser's scroll
 * restoration. Remember where each jump started, restore it on Back, and offer a visible way back.
 */
function useParagraphJumps() {
  const jumps = useRef<{ from: number; to: string }[]>([]);
  const [canReturn, setCanReturn] = useState(false);

  useEffect(() => {
    // popstate also fires when a # link is followed, so only a move away from the last jump's target is a Back.
    const onPopState = () => {
      const last = jumps.current.at(-1);
      if (!last || window.location.hash === last.to) return;
      jumps.current.pop();
      setCanReturn(jumps.current.length > 0);
      requestAnimationFrame(() => window.scrollTo({ top: last.from }));
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function onClickCapture(event: MouseEvent) {
    const link = (event.target as HTMLElement).closest<HTMLAnchorElement>('a[href^="#p-"]');
    const to = link?.getAttribute("href");
    if (!to || to === window.location.hash) return; // same target: no new history entry
    jumps.current.push({ from: window.scrollY, to });
    setCanReturn(true);
  }

  return { onClickCapture, canReturn, goBack: () => window.history.back() };
}

function BackToOrigin({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-5 right-5 z-20 rounded-full bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-lg hover:bg-indigo-700"
    >
      ↩ Back to where you were
    </button>
  );
}

export default function JudgmentView({ id }: { id: string }) {
  const [judgment, setJudgment] = useState<Judgment | null>(null);
  const [graph, setGraph] = useState<CitationGraph | null>(null);
  const [error, setError] = useState<unknown>(null);
  const hash = useHash();
  const [selectedRoles, toggleRole] = useRoleFilter();
  const [citesOnly, setCitesOnly] = useCitesFilter();
  const jumps = useParagraphJumps();

  useEffect(() => {
    api.judgment(id).then(setJudgment).catch(setError);
    api.citations(id).then(setGraph).catch(() => setGraph(null));
  }, [id]);

  // Opening a link to a paragraph scrolls to it once the text has loaded; later jumps are native anchor links.
  useEffect(() => {
    if (judgment && window.location.hash) document.getElementById(window.location.hash.slice(1))?.scrollIntoView();
  }, [judgment]);

  if (error) return <StatusMessage error={error} />;
  if (!judgment) return <p className="text-sm text-slate-500">Loading judgment…</p>;

  const seqByLabel = new Map(judgment.paragraphs.map((p) => [p.label, p.seq]));
  return (
    <article className="space-y-5" onClickCapture={jumps.onClickCapture}>
      {jumps.canReturn ? <BackToOrigin onClick={jumps.goBack} /> : null}
      <header className="space-y-1">
        <h1 className="text-xl font-semibold">{judgment.title}</h1>
        <p className="text-sm text-slate-600">
          {[judgment.neutral_citation, judgment.scr_citation, formatDate(judgment.decision_date)].filter(Boolean).join(" · ")}
        </p>
        <p className="text-sm text-slate-600">
          Bench: {judgment.bench.join(", ") || "not stated"}
          {judgment.author ? ` · Author: ${judgment.author}` : ""}
        </p>
        {judgment.acts.length ? <p className="text-sm text-slate-600">Acts: {judgment.acts.join("; ")}</p> : null}
        <a href={judgment.pdf_url} target="_blank" rel="noopener noreferrer" className="inline-block text-sm text-indigo-700 hover:underline">
          Original PDF ↗
        </a>
      </header>

      <CitationsPanel graph={graph} />
      <BreakdownPanel judgmentId={judgment.id} />
      <QuestionPanel judgmentId={judgment.id} />

      {judgment.reporter_front_matter.length ? (
        <Section title="Reporter's headnotes (prepared by the law reporter, not the court)">
          <details>
            <summary className="cursor-pointer text-sm text-indigo-700">Show headnotes</summary>
            <dl className="mt-3 space-y-3 text-sm">
              {judgment.reporter_front_matter.map((s) => (
                <div key={s.section}>
                  <dt className="font-semibold">{s.title}</dt>
                  <dd className="text-slate-700">{linkParagraphRefs(s.text, seqByLabel)}</dd>
                </div>
              ))}
            </dl>
          </details>
        </Section>
      ) : null}

      <Section title="Judgment">
        <RoleFilter selected={selectedRoles} onToggle={toggleRole} counts={roleCounts(judgment.paragraphs)} />
        <label className="mb-3 flex items-center gap-2 text-xs text-slate-700">
          <input type="checkbox" checked={citesOnly} onChange={(e) => setCitesOnly(e.target.checked)} />
          Cites cases only ({judgment.paragraphs.filter((p) => p.cites_cases).length} paragraphs)
        </label>
        {judgment.numbering_derived ? (
          <div className="mb-3">
            <Notice tone="warn">Paragraph numbers here were added by Nyaya Search; they are not in the original judgment.</Notice>
          </div>
        ) : null}
        <ol className="space-y-2">
          {visibleParagraphs(judgment.paragraphs, selectedRoles, citesOnly).map((p) => (
            <ParagraphItem key={p.seq} judgment={judgment} paragraph={p} highlighted={hash === `#p-${p.seq}`} />
          ))}
        </ol>
      </Section>
    </article>
  );
}
