-- Paragraph refers to an earlier case (citation, case name, "(supra)" or "[See: ...]"); drives the "Cites cases" filter.
ALTER TABLE paragraphs ADD COLUMN cites_cases boolean NOT NULL DEFAULT false;
CREATE INDEX paragraphs_cites_cases ON paragraphs (judgment_id) WHERE cites_cases;
