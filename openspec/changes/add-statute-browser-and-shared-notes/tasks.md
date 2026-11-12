## 1. Statute browser
- [x] 1.1 Index and section API endpoints over `judgment_acts`, with exact section matching
- [x] 1.2 Referring paragraph lookup for each section result
- [x] 1.3 Statute index and section pages on the web
- [x] 1.4 Link section mentions in judgment text to their statute page
- [x] 1.5 Tests: exact section matching (138 vs 1380), empty section, same-sentence rule

## 2. Shared research notes
- [ ] 2.1 `shared_notes` migration; create, read and revoke endpoints; ids are random UUIDs
- [ ] 2.2 Owner token returned on create and stored in the browser; revoke requires it
- [ ] 2.3 Share button with the disclosure notice; read-only note page; withdrawn page
- [ ] 2.4 Shared notes expire after 30 days unless renewed; tests for empty note, revoke, expiry, and no content in logs

## 3. Verification
- [ ] 3.1 Live test of both features on the deployed site
- [ ] 3.2 Update README (features and API) and the test scenarios
