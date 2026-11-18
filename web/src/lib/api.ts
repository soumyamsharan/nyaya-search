import type {
  Answer,
  Breakdown,
  CitationGraph,
  JudgeCount,
  Judgment,
  SearchFilters,
  SearchResponse,
  StatuteActPage,
  StatuteIndex,
  NoteCreated,
  NoteRenewed,
  SharedNote,
  StatuteSectionPage,
  Provision,
  ProvisionKind,
} from "./types";

import { HOUR, MINUTE, cached, prefetch } from "./cache";

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type ApiErrorKind = "unreachable" | "busy" | "unavailable" | "not_found" | "invalid" | "rate_limited" | "error";

export class ApiError extends Error {
  constructor(public readonly kind: ApiErrorKind, message: string) {
    super(message);
  }
}

const KIND_BY_CODE: Record<string, ApiErrorKind> = {
  llm_busy: "busy",
  llm_unavailable: "unavailable",
  not_found: "not_found",
  invalid_request: "invalid",
  rate_limited: "rate_limited",
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("unreachable", "The service is temporarily unavailable. Please try again shortly.");
  }
  if (response.status === 204) return undefined as T;
  if (response.ok) return (await response.json()) as T;
  const body = await response.json().catch(() => null);
  const code: string | undefined = body?.error?.code;
  const message: string = body?.error?.message ?? "Something went wrong. Please try again.";
  throw new ApiError((code && KIND_BY_CODE[code]) || "error", message);
}

const enc = encodeURIComponent;
const splitList = (value: string) => value.split(",").map((v) => v.trim()).filter(Boolean);

/** Form fields -> API query: comma lists become repeated `judge` / `role` parameters. */
function searchParams(q: string, filters: SearchFilters): URLSearchParams {
  const params = new URLSearchParams({ q });
  for (const [key, value] of Object.entries(filters)) {
    if (!value) continue;
    if (key === "judge") splitList(value).forEach((j) => params.append("judge", j));
    else if (key === "match_in") splitList(value).forEach((r) => params.append("role", r));
    else params.set(key, value);
  }
  return params;
}

/** Read-only GET, kept in the session cache for `ttl` ms. Notes and questions are never cached. */
function get<T>(path: string, ttl: number): Promise<T> {
  return cached(path, ttl, () => request<T>(path));
}

const judgmentPath = (id: string) => `/v1/judgments/${enc(id)}`;
const citationsPath = (id: string) => `/v1/judgments/${enc(id)}/citations`;

export const api = {
  search(q: string, filters: SearchFilters): Promise<SearchResponse> {
    return get(`/v1/search?${searchParams(q, filters)}`, 10 * MINUTE);
  },
  judges: () => get<{ judges: JudgeCount[] }>("/v1/judges", HOUR).then((r) => r.judges),
  statutes: () => get<StatuteIndex>("/v1/statutes", 30 * MINUTE),
  createNote: (items: { judgment_id: string; label: string }[]) =>
    request<NoteCreated>("/v1/notes", { method: "POST", body: JSON.stringify({ items }) }),
  getNote: (id: string) => request<SharedNote>(`/v1/notes/${enc(id)}`),
  renewNote: (id: string, token: string) =>
    request<NoteRenewed>(`/v1/notes/${enc(id)}/renewal`, { method: "POST", headers: { "X-Note-Token": token } }),
  revokeNote: (id: string, token: string) =>
    request<void>(`/v1/notes/${enc(id)}`, { method: "DELETE", headers: { "X-Note-Token": token } }),
  statuteAct: (key: string, page: number) => get<StatuteActPage>(`/v1/statutes/${enc(key)}?page=${page}`, 30 * MINUTE),
  statuteSection: (key: string, section: string) =>
    get<StatuteSectionPage>(`/v1/statutes/${enc(key)}/sections/${enc(section)}`, 30 * MINUTE),
  provision: (kind: ProvisionKind, key: string, slug: string) =>
    get<Provision>(`/v1/provisions/${kind}/${enc(key)}/${enc(slug)}`, 30 * MINUTE),
  judgment: (id: string) => get<Judgment>(judgmentPath(id), HOUR),
  breakdown: (id: string) => get<Breakdown>(`/v1/judgments/${enc(id)}/breakdown`, HOUR),
  citations: (id: string) => get<CitationGraph>(citationsPath(id), HOUR),
  /** Warm the cache for a judgment the user is about to open. */
  prefetchJudgment(id: string): void {
    prefetch(judgmentPath(id), HOUR, () => request<Judgment>(judgmentPath(id)));
    prefetch(citationsPath(id), HOUR, () => request<CitationGraph>(citationsPath(id)));
  },
  ask: (id: string, question: string) =>
    request<Answer>(`/v1/judgments/${enc(id)}/questions`, { method: "POST", body: JSON.stringify({ question }) }),
};
