## ADDED Requirements

### Requirement: One model call at a time
The server SHALL run one language-model call at a time. A second call SHALL wait its turn for up to 45 seconds and SHALL
fail with a busy message if its turn does not come in that time.

#### Scenario: Question and breakdown together
- **WHEN** a user asks a question and opens a breakdown at the same time
- **THEN** the second request waits for the first to finish, and the user sees only its spinner

### Requirement: Provider rate limits are waited out
When the model provider answers with a rate limit (HTTP 429), the server SHALL wait for the time the provider asks for, up
to 20 seconds in total, and try again before failing the request.

#### Scenario: Short rate limit
- **WHEN** the provider's rate limit clears within the wait
- **THEN** the request succeeds without the user seeing an error

#### Scenario: Long rate limit
- **WHEN** the rate limit does not clear within 20 seconds
- **THEN** the request fails with the busy message

### Requirement: Generic busy message
When an AI request fails because of a rate limit, a daily limit or a provider failure, the user SHALL see one message:
"AI answers are busy right now. Please try again in a minute — search and reading still work." The reason SHALL be recorded
in the logs and SHALL NOT be shown to the user.

#### Scenario: Busy message
- **WHEN** an AI request fails
- **THEN** the message does not mention limits, queues or costs

### Requirement: Breakdown size fits the provider's request limit
The paragraphs sent for a breakdown SHALL be limited to 3,500 estimated tokens (four characters per token), leaving room for
the instructions and the answer under the provider's per-request limit.

#### Scenario: Long judgment
- **WHEN** a judgment is longer than the budget
- **THEN** the headnote-referenced paragraphs and the opening and closing paragraphs are kept first, and the rest is cut

### Requirement: Token-based daily limit (open)
The daily AI limit SHALL be counted in tokens used per day, not calls, so requests stop before the provider's daily token
allowance is spent. This requirement is open and not yet built.

#### Scenario: Daily allowance reached
- **WHEN** the day's tokens are close to the provider's daily allowance
- **THEN** further AI requests show the busy message without being sent
