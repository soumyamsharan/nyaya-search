import type {
  Answer,
  Breakdown,
  CitationGraph,
  JudgeCount,
  Judgment,
  SearchFilters,
  SearchResponse,
  StatuteIndex,
  StatuteSectionPage,
} from "./types";

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

export const api = {
  search(q: string, filters: SearchFilters): Promise<SearchResponse> {
    return request(`/v1/search?${searchParams(q, filters)}`);
  },
  judges: () => request<{ judges: JudgeCount[] }>("/v1/judges").then((r) => r.judges),
  statutes: () => request<StatuteIndex>("/v1/statutes"),
  statuteSection: (key: string, section: string) =>
    request<StatuteSectionPage>(`/v1/statutes/${enc(key)}/sections/${enc(section)}`),
  judgment: (id: string) => request<Judgment>(`/v1/judgments/${enc(id)}`),
  breakdown: (id: string) => request<Breakdown>(`/v1/judgments/${enc(id)}/breakdown`),
  citations: (id: string) => request<CitationGraph>(`/v1/judgments/${enc(id)}/citations`),
  ask: (id: string, question: string) =>
    request<Answer>(`/v1/judgments/${enc(id)}/questions`, { method: "POST", body: JSON.stringify({ question }) }),
};
