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

export interface StatuteRef {
  raw: string;
  key: string;
  name: string;
  section: string;
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
