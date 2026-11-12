## Purpose

Makes Nyaya Search available to anyone on a stable public HTTPS link, opened in an ordinary browser with no setup, and keeps it usable and affordable when strangers use it.

## ADDED Requirements

### Requirement: Stable public HTTPS link
The website SHALL be reachable at one stable HTTPS address that does not change between deployments, and visitors SHALL need only a current desktop or mobile browser: no account, install, VPN or configuration. Plain HTTP requests SHALL redirect to HTTPS.

#### Scenario: First-time visitor
- **WHEN** someone opens the link on their own laptop on any network
- **THEN** the search page loads over HTTPS and a search can be run without signing in or installing anything

#### Scenario: Redeploy keeps the link
- **WHEN** a new version is deployed
- **THEN** the same link serves the new version

#### Scenario: HTTP request
- **WHEN** a visitor requests the site or API over plain HTTP
- **THEN** they are redirected to HTTPS

### Requirement: Runs without the developer's machine, on free hosting
The site SHALL stay available without the developer's machine, on hosting that costs nothing. Because the free API host may put the service to sleep after a long idle period (about 48 hours), a visit to a sleeping service SHALL wake it, and the website SHALL tell the visitor the service is waking up and to retry shortly, rather than showing a raw error.

#### Scenario: First visit after days of no traffic
- **WHEN** nobody has used the site for several days and a visitor runs a search
- **THEN** the website says the service is waking up, and searches work normally once it has started

#### Scenario: Developer laptop off
- **WHEN** the developer's Mac is switched off
- **THEN** the site keeps working

### Requirement: Only the web entry points are exposed
From the internet, only HTTPS on the website and API hostnames SHALL be reachable; the database and internal service ports SHALL NOT be reachable (the database listens only inside the API container), and any server administration SHALL require key-based authentication.

#### Scenario: Port scan
- **WHEN** someone probes the API's public address
- **THEN** only HTTPS answers, and the database is not reachable

### Requirement: Secrets stay on the server
API keys and database credentials SHALL exist only in server-side configuration and SHALL NOT appear in the browser bundle, page source, API responses or the source repository.

#### Scenario: Inspecting the site
- **WHEN** a visitor inspects the web app's code and network traffic
- **THEN** no LLM key or database credential is visible

### Requirement: Daily cap on LLM use
The system SHALL enforce a configurable daily limit on language-model calls across all visitors, in addition to per-IP rate limits. When the cap or the provider's quota is reached, breakdowns and follow-up questions SHALL show a "busy, try later" state while search, judgment text, reporter headnotes, citations and export keep working.

#### Scenario: Cap reached
- **WHEN** the daily LLM cap has been used up
- **THEN** a visitor asking a follow-up question sees a "busy, try later" message, and searching and reading judgments still work

#### Scenario: Cached breakdown after cap
- **WHEN** the cap is reached and a visitor opens a judgment whose breakdown is already cached
- **THEN** the cached breakdown is shown

### Requirement: Friendly failure states
When the API is unreachable, the website SHALL show a clear "service temporarily unavailable" page instead of a blank screen or raw error.

#### Scenario: API down
- **WHEN** the API server is down and a visitor opens the site
- **THEN** the page loads and shows a "temporarily unavailable" message

### Requirement: Uptime monitoring and backups
The deployment SHALL be checked from outside at least every 5 minutes with an alert to the developer on failure, and the database SHALL be backed up at least daily to storage separate from the server's disk, with a documented restore procedure that has been run once.

#### Scenario: Site goes down
- **WHEN** the health check fails
- **THEN** the developer is alerted

#### Scenario: Restore drill
- **WHEN** the latest backup is restored to an empty database
- **THEN** search returns the same results as production for a sample query
