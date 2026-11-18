## 1. Search pickers
- [x] 1.1 Searchable dropdowns for judges, author, outcome, match in, Act and section
- [x] 1.2 Dropdown arrow on every picker; full option names
- [x] 1.3 Act matches by key words; section choices follow the chosen Act
- [x] 1.4 Date fields with typing, calendar, and month and year selection
- [ ] 1.5 Test a search with several filters combined end to end

## 2. Visual design
- [x] 2.1 Editorial theme tokens, serif headings and judgment text
- [x] 2.2 Ruled results list with underlined titles; collapsible Refine panel
- [x] 2.3 Pointer cursor on clickable elements
- [ ] 2.4 Check the statute, notes and share pages in the browser after the restyle

## 3. Loading and caching
- [x] 3.1 Spinners on buttons; placeholders on results, judgments and statute pages
- [x] 3.2 Session cache for read-only responses; notes and questions excluded
- [x] 3.3 Hover prefetch of judgments

## 4. AI requests
- [x] 4.1 One model call at a time with a 45 second queue
- [x] 4.2 Provider rate limits retried for up to 20 seconds
- [x] 4.3 One generic busy message; reasons logged only
- [x] 4.4 Breakdown paragraph budget lowered to 3,500 estimated tokens
- [ ] 4.5 Token-based daily limit (see ai-requests spec, open)
- [ ] 4.6 Handle "request too large" from the provider with a clear message
- [ ] 4.7 Live parallel test on a judgment with no saved breakdown, after the quota resets

## 5. Platform
- [x] 5.1 Next.js upgraded to 16.4.6 (clears the moderate advisory)
- [x] 5.2 Corpus scope stated in the corpus-coverage spec
