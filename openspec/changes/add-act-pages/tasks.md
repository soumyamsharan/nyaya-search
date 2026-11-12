## 0. Blocked: source confirmation
- [x] 0.1 Confirm India Code's URL format and linking terms: /handle/123456789/<id> redirects to the Act's item page; the policy allows direct links with notification, a new window, no framing, and no endorsement implied. Prohibits automated scraping.

## 1. Act page
- [x] 1.1 `GET /v1/statutes/{key}` with pagination and per-judgment section lists; tests
- [x] 1.2 Act page and links from Act names in the index, section pages and judgment text

## 2. About this Act
- [ ] 2.1 `acts.yaml` for the top ~30 Acts: description, reviewer, review date, official URL
- [ ] 2.2 Review each description against the official Act; record the reviewer and date
- [ ] 2.3 About section on the Act page; tests that uncurated Acts show no description

## 3. Verification
- [ ] 3.1 Live check of the Act pages and About section on the deployed site
