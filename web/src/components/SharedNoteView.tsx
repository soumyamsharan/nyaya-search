"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SharedNote } from "@/lib/types";
import { Notice, Section, StatusMessage, formatDate } from "./ui";

export default function SharedNoteView({ id }: { id: string }) {
  const [note, setNote] = useState<SharedNote | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.getNote(id).then(setNote).catch(setError);
  }, [id]);

  if (error) return <StatusMessage error={error} />;
  if (!note) return <p className="text-sm text-slate-500">Loading note…</p>;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Shared research note</h1>
      <p className="text-sm text-slate-600">
        Read-only. Available until {formatDate(note.expires_at)}. Read each judgment before citing it.
      </p>
      <ol className="space-y-3">
        {note.items.map((item, i) => (
          <li key={i}>
            <Section title={item.judgment ? item.judgment.title : "Judgment no longer available"}>
              {item.judgment ? (
                <p className="text-xs text-slate-500">
                  {[item.judgment.citation, formatDate(item.judgment.decision_date)].filter(Boolean).join(" · ")}
                </p>
              ) : null}
              {item.text ? (
                <blockquote className="mt-2 border-l-4 border-indigo-200 pl-3 text-sm text-slate-800">
                  “{item.text}”
                  <span className="mt-1 block text-xs text-slate-500">
                    — {item.judgment?.title}, {item.judgment?.citation}, ¶{item.label}
                  </span>
                </blockquote>
              ) : (
                <Notice>This paragraph is no longer in the corpus (¶{item.label}).</Notice>
              )}
              {item.judgment ? (
                <Link
                  href={`/judgments/${item.judgment.id}#p-${item.label}`}
                  className="mt-2 inline-block text-xs text-indigo-700 hover:underline"
                >
                  Open in judgment ↗
                </Link>
              ) : null}
            </Section>
          </li>
        ))}
      </ol>
    </div>
  );
}
