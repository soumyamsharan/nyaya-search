"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { type NoteItem, loadNotes } from "@/lib/notes";
import { type SharedLink, loadSharedLinks, saveSharedLinks, shareUrl } from "@/lib/shared-notes";

const DISCLOSURE =
  "Anyone with the link can read these paragraphs, citations and your note's order. The link does not show your " +
  "searches, questions or other notes. It works for 30 days unless you renew it, and you can withdraw it at any time.";

export default function ShareNote({ onClose }: { onClose: () => void }) {
  // Read once when the panel opens (it only mounts after a click, so the browser storage is available).
  const [items] = useState<NoteItem[]>(() => loadNotes());
  const [links, setLinks] = useState<SharedLink[]>(() => loadSharedLinks());
  const [confirming, setConfirming] = useState(false);
  const [created, setCreated] = useState<SharedLink | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function create() {
    setBusy(true);
    setMessage(null);
    try {
      const body = await api.createNote(items.map((i) => ({ judgment_id: i.judgmentId, label: i.label })));
      const link: SharedLink = {
        id: body.id,
        ownerToken: body.owner_token,
        createdAt: new Date().toISOString(),
        expiresAt: body.expires_at,
        count: items.length,
      };
      const next = [link, ...loadSharedLinks()];
      saveSharedLinks(next);
      setLinks(next);
      setCreated(link);
      setConfirming(false);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Could not create the link. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function renew(link: SharedLink) {
    try {
      const body = await api.renewNote(link.id, link.ownerToken);
      const next = loadSharedLinks().map((l) => (l.id === link.id ? { ...l, expiresAt: body.expires_at } : l));
      saveSharedLinks(next);
      setLinks(next);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Could not renew the link.");
    }
  }

  async function revoke(link: SharedLink) {
    try {
      await api.revokeNote(link.id, link.ownerToken);
    } catch (e) {
      // already withdrawn or expired: still remove it from this browser's list
      if (!(e instanceof ApiError && e.kind === "not_found")) {
        setMessage(e instanceof ApiError ? e.message : "Could not withdraw the link.");
        return;
      }
    }
    const next = loadSharedLinks().filter((l) => l.id !== link.id);
    saveSharedLinks(next);
    setLinks(next);
    if (created?.id === link.id) setCreated(null);
  }

  return (
    <div className="absolute right-0 top-full z-30 mt-2 w-[min(28rem,90vw)] space-y-3 rounded-lg border border-slate-200 bg-white p-4 text-sm shadow-xl">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Share your research note</h2>
        <button onClick={onClose} className="text-slate-500 hover:text-slate-800" aria-label="Close">
          ✕
        </button>
      </div>

      {created ? (
        <div className="space-y-2">
          <p>Your link:</p>
          <p className="break-all rounded bg-slate-50 p-2 font-mono text-xs">{shareUrl(created.id)}</p>
          <button
            onClick={() => navigator.clipboard?.writeText(shareUrl(created.id))}
            className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50"
          >
            Copy link
          </button>
        </div>
      ) : items.length === 0 ? (
        <p className="text-slate-600">Your note is empty. Add paragraphs with “Add to note” first.</p>
      ) : confirming ? (
        <div className="space-y-2">
          <p className="text-amber-900">{DISCLOSURE}</p>
          <div className="flex gap-2">
            <button
              onClick={create}
              disabled={busy}
              className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
            >
              {busy ? "Creating…" : "I understand, create the link"}
            </button>
            <button onClick={() => setConfirming(false)} className="text-xs text-slate-600 hover:underline">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setConfirming(true)}
          className="rounded border border-indigo-300 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-50"
        >
          Create a link to this note ({items.length} paragraph{items.length === 1 ? "" : "s"})
        </button>
      )}

      {message ? <p className="text-red-700">{message}</p> : null}

      {links.length ? (
        <div className="space-y-2 border-t border-slate-200 pt-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Your shared links</h3>
          <ul className="space-y-2">
            {links.map((link) => (
              <li key={link.id} className="flex flex-wrap items-center gap-2 text-xs">
                <span className="text-slate-600">
                  {link.count} paragraph{link.count === 1 ? "" : "s"}, until{" "}
                  {new Date(link.expiresAt).toLocaleDateString("en-IN")}
                </span>
                <button onClick={() => renew(link)} className="text-indigo-700 hover:underline">
                  Renew 30 days
                </button>
                <button onClick={() => revoke(link)} className="text-red-700 hover:underline">
                  Withdraw
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
