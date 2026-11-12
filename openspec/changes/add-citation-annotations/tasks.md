## 1. Parser and citation formats
- [x] 1.1 Quoted-numbering rule: resume only when the judgment's numbering continues (tests for quoted runs and statute clauses)
- [x] 1.2 Re-extract all judgments (extractor version 5)
- [x] 1.3 AIR High Court, Delhi Law Times and English report formats, with tests

## 2. Cites-cases flag
- [x] 2.1 `cites_cases()` in text.py; migration 005; the citations stage sets the flag
- [x] 2.2 Rebuild citations on the corpus and check coverage

## 3. API and web
- [x] 3.1 Paragraph `cites_cases` and `references` in judgment responses
- [x] 3.2 "Cites cases only" toggle (URL-shareable), combined with role chips
- [x] 3.3 Inline highlights: links for cited judgments in the corpus, "not in corpus" otherwise

## 4. Verification
- [x] 4.1 Verify 2025_5_458_474 in the browser: the cites-cases filter should show ¶29, 32, 33, 36, 39, 40, 42, 43
- [x] 4.2 Full unit and integration test run; commit
