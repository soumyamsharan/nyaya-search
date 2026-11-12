-- Machine-assigned role of each paragraph (facts, issue, arguments, statute, precedent, reasoning, conclusion).
ALTER TABLE paragraphs ADD COLUMN role text;
CREATE INDEX paragraphs_role ON paragraphs (role);
