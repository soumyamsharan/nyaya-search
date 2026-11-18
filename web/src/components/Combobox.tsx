"use client";

import { type KeyboardEvent, useId, useState } from "react";

export interface Option {
  value: string;
  label: string;
  hint?: string; // right-aligned detail, e.g. how many judgments
  keywords?: string; // extra words that should match too, e.g. the full name of an Act
}

const MAX_SHOWN = 40;

/** The text the user is currently typing. For a comma-separated list, only the part after the last comma. */
function typedToken(text: string, multi: boolean): string {
  return (multi ? text.split(",").pop() ?? "" : text).trim();
}

function filterOptions(options: Option[], token: string): Option[] {
  const q = token.toLowerCase();
  if (!q) return options;
  const matching = options.filter((o) => `${o.label} ${o.value} ${o.keywords ?? ""}`.toLowerCase().includes(q));
  // Names that start with the typed text come first.
  return matching.sort((a, b) => Number(!b.label.toLowerCase().startsWith(q)) - Number(!a.label.toLowerCase().startsWith(q)));
}

interface ComboboxProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  placeholder?: string;
  emptyText?: string;
  /** Whatever the user types can be kept, not only the listed options (judges, Act, section). */
  freeText?: boolean;
  /** Comma-separated list, e.g. several judges on the bench. */
  multi?: boolean;
}

/**
 * A text box with a dropdown that narrows as you type. Arrow keys move through the list, Enter picks,
 * Escape closes. Picking an option never clears what the user typed until they choose.
 */
export default function Combobox({ id, label, value, onChange, options, placeholder, emptyText, freeText, multi }: ComboboxProps) {
  const listId = useId();
  const [query, setQuery] = useState<string | null>(null); // null: not editing, show the chosen value
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const display = freeText ? value : options.find((o) => o.value === value)?.label ?? value;
  const text = query ?? display;
  // Right after focusing (text still equals the chosen value) show every option instead of filtering by it.
  const token = query === null || query === display ? "" : typedToken(text, !!multi);
  const shown = filterOptions(options, token).slice(0, MAX_SHOWN);

  function commit(next: string) {
    onChange(multi ? next.split(",").map((s) => s.trim()).filter(Boolean).join(", ") : next.trim());
  }

  function choose(option: Option) {
    if (multi) {
      const parts = text.split(",");
      parts[parts.length - 1] = ` ${option.value}`;
      const next = parts.map((s) => s.trim()).filter(Boolean).join(", ");
      onChange(next);
      setQuery(`${next}, `); // keep the list open so another judge can be added
      setActive(0);
      return;
    }
    onChange(option.value);
    setQuery(null);
    setOpen(false);
  }

  function leave() {
    if (freeText && query !== null) commit(query);
    setQuery(null);
    setOpen(false);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, shown.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter") {
      if (open && shown[active]) {
        event.preventDefault();
        choose(shown[active]);
      } else if (freeText) {
        event.preventDefault();
        commit(text);
        setQuery(null);
        setOpen(false);
      }
    } else if (event.key === "Escape") {
      setQuery(null);
      setOpen(false);
    }
  }

  const showList = open && (shown.length > 0 || Boolean(emptyText));
  const activeId = showList && shown[active] ? `${listId}-${active}` : undefined;

  return (
    <div className="relative">
      <label htmlFor={id} className="flex min-h-8 items-end text-xs font-medium leading-4 text-ink-soft">
        {label}
      </label>
      <input
        id={id}
        type="text"
        role="combobox"
        autoComplete="off"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={activeId}
        value={text}
        placeholder={placeholder}
        onFocus={(e) => {
          setQuery(display);
          setOpen(true);
          setActive(0);
          e.currentTarget.select();
        }}
        onBlur={leave}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onKeyDown={onKeyDown}
        className="mt-1.5 block h-9 w-full min-w-0 rounded border border-rule bg-white px-2.5 text-sm text-ink placeholder:text-muted/70"
      />
      {showList ? (
        <ul
          id={listId}
          role="listbox"
          onMouseDown={(e) => e.preventDefault()} // keep focus in the input so the pick registers before blur
          className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-md border border-rule bg-surface py-1 text-sm shadow-sm"
        >
          {shown.length === 0 ? (
            <li className="px-3 py-2 text-xs text-muted">{emptyText}</li>
          ) : (
            shown.map((option, index) => (
              <li
                key={option.value}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={index === active}
                onMouseEnter={() => setActive(index)}
                onClick={() => choose(option)}
                className={`flex cursor-pointer items-baseline justify-between gap-3 px-3 py-1.5 ${
                  index === active ? "bg-accent-soft text-ink" : "text-ink-soft"
                }`}
              >
                <span className="min-w-0 truncate">{option.label}</span>
                {option.hint ? <span className="shrink-0 text-xs tabular-nums text-muted">{option.hint}</span> : null}
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
