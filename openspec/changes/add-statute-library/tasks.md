## 1. Extraction
- [x] 1.1 Article references (Constitution) with exact numbers; tests
- [x] 1.2 Rule and Regulation references, with the parent Act in the same sentence where it exists; tests
- [x] 1.3 Notification and Ordinance references; tests
- [x] 1.4 Store the kinds in the database (migration) and rebuild from the corpus

## 2. API and pages
- [x] 2.1 Provision endpoint per statute provision (GET /v1/provisions/{kind}/{key}/{slug})
- [ ] 2.2 Paginated list endpoints for articles, rules, regulations and notifications; the statute index lists Acts only
- [x] 2.3 Provision page for every kind, with referring judgments, related judgments and the India Code search link
- [ ] 2.4 "Rules, parent not identified" group

## 3. Descriptions
- [x] 3.1 Descriptions show only when written in the data file; none written yet
- [ ] 3.2 Write descriptions for the curated list (top Acts first)
- [ ] 3.3 Confirm the India Code linking notice has been sent (policy asks for it)

## 4. Verification
- [x] 4.1 Live API check for Section 138 and Article 21
- [ ] 4.2 Live browser check of rule, regulation and notification pages
