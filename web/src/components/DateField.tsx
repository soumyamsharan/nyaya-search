"use client";

import { useEffect, useId, useRef, useState } from "react";

const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

// Newest first, back to 1950: judgments and the dates users search for span decades.
const YEARS = Array.from({ length: new Date().getFullYear() + 1 - 1950 }, (_, i) => new Date().getFullYear() + 1 - i);

const pad = (n: number) => String(n).padStart(2, "0");
const toIso = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`;
const displayDate = (iso: string) => (iso ? iso.split("-").reverse().join("/") : "");

/** Accepts dd/mm/yyyy or yyyy-mm-dd and returns yyyy-mm-dd, or null when the text is not a real date. */
function parseDate(text: string): string | null {
  const t = text.trim();
  const dmy = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(t);
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(t);
  const [y, m, d] = dmy ? [Number(dmy[3]), Number(dmy[2]), Number(dmy[1])] : iso ? [Number(iso[1]), Number(iso[2]), Number(iso[3])] : [0, 0, 0];
  if (!y || m < 1 || m > 12 || d < 1) return null;
  const date = new Date(Date.UTC(y, m - 1, d));
  return date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d ? toIso(y, m - 1, d) : null;
}

interface DateFieldProps {
  id: string;
  label: string;
  value: string; // yyyy-mm-dd or ""
  onChange: (value: string) => void;
}

/** A date box you can type into, with a calendar that opens from the button. Dates are sent as yyyy-mm-dd. */
export default function DateField({ id, label, value, onChange }: DateFieldProps) {
  const popoverId = useId();
  const root = useRef<HTMLDivElement>(null);
  const today = new Date();
  const selected = value ? value.split("-").map(Number) : null;
  const [open, setOpen] = useState(false);
  const [text, setText] = useState<string | null>(null); // null: show the chosen date
  const [view, setView] = useState(() => ({
    year: selected?.[0] ?? today.getFullYear(),
    month: (selected?.[1] ?? today.getMonth() + 1) - 1,
  }));

  // Close the calendar on any click outside this field.
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    return () => document.removeEventListener("mousedown", onPointer);
  }, [open]);

  function pick(iso: string) {
    onChange(iso);
    setText(null);
    setOpen(false);
  }

  function jump(next: { year?: number; month?: number }) {
    setView((v) => ({ year: next.year ?? v.year, month: next.month ?? v.month }));
  }

  function shift(months: number) {
    setView((v) => {
      const next = new Date(Date.UTC(v.year, v.month + months, 1));
      return { year: next.getUTCFullYear(), month: next.getUTCMonth() };
    });
  }

  // Monday-first grid: leading blanks, then the days of the month.
  const firstWeekday = (new Date(Date.UTC(view.year, view.month, 1)).getUTCDay() + 6) % 7;
  const daysInMonth = new Date(Date.UTC(view.year, view.month + 1, 0)).getUTCDate();
  const cells: (number | null)[] = [...Array(firstWeekday).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)];

  return (
    <div ref={root} className="relative">
      <label htmlFor={id} className="flex min-h-8 items-end text-xs font-medium leading-4 text-ink-soft">
        {label}
      </label>
      <div className="mt-1.5 flex h-9 items-stretch rounded border border-rule bg-white">
        <input
          id={id}
          type="text"
          inputMode="numeric"
          placeholder="dd/mm/yyyy"
          value={text ?? displayDate(value)}
          onFocus={() => setText(displayDate(value))}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => {
            if (text === null) return;
            const parsed = text.trim() === "" ? "" : parseDate(text);
            if (parsed !== null) onChange(parsed);
            setText(null);
          }}
          onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
          className="min-w-0 flex-1 rounded-l bg-transparent px-2.5 text-sm text-ink placeholder:text-muted/70"
        />
        {value ? (
          <button
            type="button"
            onClick={() => onChange("")}
            aria-label={`Clear ${label}`}
            className="px-2 text-muted hover:text-ink"
          >
            ×
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-controls={popoverId}
          aria-label={`Open calendar for ${label}`}
          className="border-l border-rule px-2.5 text-ink-soft hover:bg-accent-soft"
        >
          <svg viewBox="0 0 20 20" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
            <rect x="3" y="4.5" width="14" height="12.5" rx="1.5" />
            <path d="M3 8.5h14M7 3v3M13 3v3" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {open ? (
        <div id={popoverId} className="absolute z-20 mt-1 w-64 rounded-md border border-rule bg-surface p-3 shadow-sm">
          <div className="mb-2 flex items-center gap-1.5">
            <button type="button" onClick={() => shift(-1)} className="size-7 shrink-0 rounded text-ink-soft hover:bg-accent-soft" aria-label="Previous month">
              ‹
            </button>
            <select
              aria-label="Month"
              value={view.month}
              onChange={(e) => jump({ month: Number(e.target.value) })}
              className="h-7 min-w-0 flex-1 rounded border border-rule bg-white px-1 text-sm text-ink"
            >
              {MONTHS.map((name, i) => (
                <option key={name} value={i}>
                  {name}
                </option>
              ))}
            </select>
            <select
              aria-label="Year"
              value={view.year}
              onChange={(e) => jump({ year: Number(e.target.value) })}
              className="h-7 w-20 shrink-0 rounded border border-rule bg-white px-1 text-sm text-ink"
            >
              {YEARS.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
            <button type="button" onClick={() => shift(1)} className="size-7 shrink-0 rounded text-ink-soft hover:bg-accent-soft" aria-label="Next month">
              ›
            </button>
          </div>
          <div className="grid grid-cols-7 gap-y-1 text-center text-[0.7rem] text-muted">
            {WEEKDAYS.map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>
          <div className="mt-1 grid grid-cols-7 gap-y-1 text-center text-sm">
            {cells.map((day, i) => {
              if (day === null) return <span key={`blank-${i}`} />;
              const iso = toIso(view.year, view.month, day);
              const isSelected = iso === value;
              const isToday = iso === toIso(today.getFullYear(), today.getMonth(), today.getDate());
              return (
                <button
                  key={iso}
                  type="button"
                  onClick={() => pick(iso)}
                  className={`mx-auto size-8 rounded text-sm tabular-nums ${
                    isSelected ? "bg-accent text-white" : isToday ? "border border-accent text-accent" : "text-ink hover:bg-accent-soft"
                  }`}
                >
                  {day}
                </button>
              );
            })}
          </div>
          <div className="mt-3 flex justify-between border-t border-rule pt-2 text-xs">
            <button type="button" onClick={() => pick(toIso(today.getFullYear(), today.getMonth(), today.getDate()))} className="text-accent hover:underline">
              Today
            </button>
            <button type="button" onClick={() => onChange("")} className="text-muted hover:underline">
              Clear
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
