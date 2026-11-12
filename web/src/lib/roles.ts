// Paragraph roles (machine-assigned by the ingestion pipeline) and how the UI names and colours them.

export type Role =
  | "facts"
  | "issue"
  | "petitioner_argument"
  | "respondent_argument"
  | "statute"
  | "precedent"
  | "reasoning"
  | "conclusion";

export const ROLES: { role: Role; label: string; tone: string }[] = [
  { role: "facts", label: "Facts", tone: "bg-slate-100 text-slate-700" },
  { role: "issue", label: "Issue", tone: "bg-purple-100 text-purple-800" },
  { role: "petitioner_argument", label: "Petitioner's argument", tone: "bg-sky-100 text-sky-800" },
  { role: "respondent_argument", label: "Respondent's argument", tone: "bg-cyan-100 text-cyan-800" },
  { role: "statute", label: "Statute", tone: "bg-amber-100 text-amber-800" },
  { role: "precedent", label: "Precedent", tone: "bg-orange-100 text-orange-800" },
  { role: "reasoning", label: "Court's reasoning", tone: "bg-emerald-100 text-emerald-800" },
  { role: "conclusion", label: "Conclusion", tone: "bg-rose-100 text-rose-800" },
];

export const roleInfo = (role: Role | null) => ROLES.find((r) => r.role === role);

/** Presets for "match only in" on the search page; the value is a comma-separated role list. */
export const MATCH_IN: { value: string; label: string }[] = [
  { value: "", label: "Anywhere in the judgment" },
  { value: "reasoning,conclusion", label: "Court's reasoning & conclusion" },
  { value: "petitioner_argument,respondent_argument", label: "Arguments" },
  { value: "facts,issue", label: "Facts & issues" },
  { value: "precedent", label: "Discussion of precedents" },
  { value: "statute", label: "Statutory provisions" },
];

export const parseRoles = (value: string | null): Role[] =>
  (value ?? "").split(",").filter((r): r is Role => ROLES.some((x) => x.role === r));
