// Mirrors the API's response models (see /docs on the API).
import type { Role } from "./roles";

export interface ParagraphRef {
  seq: number;
  label: string;
}

export interface CitationRef {
  raw: string;
  judgment_id: string | null;
  title: string | null;
  citation: string | null;
}

export const PROVISION_KINDS = ["section", "article", "rule", "regulation", "notification"] as const;
export type ProvisionKind = (typeof PROVISION_KINDS)[number];

export interface StatuteRef {
  raw: string;
  kind: ProvisionKind;
  key: string;
  name: string;
  number: string;
  slug: string;
}

export interface Paragraph extends ParagraphRef {
  text: string;
  label_derived: boolean;
  role: Role | null;
  cites_cases: boolean;
  references: CitationRef[];
  statutes: StatuteRef[];
}

export interface StatuteSummary {
  key: string;
  name: string;
  judgments: number;
  sections: { section: string; judgments: number }[];
}

export interface StatuteIndex {
  acts: StatuteSummary[];
}

export interface StatuteSectionPage {
  key: string;
  name: string;
  section: string;
  judgments: { judgment: JudgmentSummary; paragraphs: { label: string; text: string }[] }[];
}

export interface ProvisionJudgment {
  judgment: JudgmentSummary;
  paragraphs: { label: string; text: string }[];
}

export interface RelatedParagraph {
  judgment: JudgmentSummary;
  label: string;
  text: string;
}

export interface Provision {
  kind: ProvisionKind;
  key: string;
  name: string;
  number: string;
  judgments_total: number;
  judgments: ProvisionJudgment[];
  related: RelatedParagraph[];
  official_url: string;
  description: string | null;
  reviewed_by: string | null;
  reviewed_on: string | null;
}

export interface JudgmentSummary {
  id: string;
  title: string;
  decision_date: string | null;
  bench: string[];
  citation: string | null;
  cited_by_count: number;
}

export interface FrontMatterSection {
  section: string;
  title: string;
  text: string;
}

export interface Judgment extends JudgmentSummary {
  author: string | null;
  neutral_citation: string | null;
  scr_citation: string | null;
  disposal_nature: string | null;
  pdf_url: string;
  acts: string[];
  reporter_front_matter: FrontMatterSection[];
  paragraphs: Paragraph[];
  numbering_derived: boolean;
}

export interface SearchResult {
  judgment: JudgmentSummary;
  matched_paragraph: Paragraph;
  score: number;
}

export interface SearchResponse {
  query_type: "fact_pattern" | "citation";
  results: SearchResult[];
  message: string | null;
  suggestion: string | null;
}

export interface JudgeCount {
  name: string;
  judgments: number;
}

export interface CitedSentence {
  text: string;
  paragraphs: ParagraphRef[];
}

export interface Breakdown {
  facts: CitedSentence[];
  issues: CitedSentence[];
  held: CitedSentence[];
  ratio: CitedSentence[];
  model: string;
  machine_generated: boolean;
}

export interface Answer {
  answered: boolean;
  sentences: CitedSentence[];
  message: string | null;
  machine_generated: boolean;
}

export interface CitationLink {
  judgment: JudgmentSummary;
  paragraph: ParagraphRef;
  overruling_language: boolean;
  paragraph_text: string | null;
}

export interface CitationGraph {
  cites: CitationLink[];
  cited_by: CitationLink[];
  unresolved: { raw: string; paragraph: ParagraphRef }[];
  overruling_evidence: CitationLink[];
}

/** Search form state; every value is the raw text of a form field (also the URL query parameter). */
export interface SearchFilters {
  year_from?: string;
  year_to?: string;
  date_from?: string;
  date_to?: string;
  judge?: string; // comma-separated: every judge must be on the bench
  author?: string;
  outcome?: string;
  match_in?: string; // comma-separated roles
  act?: string;
  section?: string;
}

export interface NoteCreated {
  id: string;
  owner_token: string;
  expires_at: string;
}

export interface NoteRenewed {
  expires_at: string;
}

export interface SharedNote {
  id: string;
  expires_at: string;
  items: { judgment: JudgmentSummary | null; label: string; text: string | null }[];
}

export interface StatuteActPage {
  key: string;
  name: string;
  judgments_total: number;
  page: number;
  per_page: number;
  judgments: { judgment: JudgmentSummary; sections: string[] }[];
}
