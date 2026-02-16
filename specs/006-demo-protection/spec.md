# Feature Specification: Demo Quota Protection Middleware

**Feature Branch**: `[006-demo-protection]`  
**Created**: 2026-02-16  
**Status**: Draft  
**Input**: User description: "Feature: Demo Quota Protection Middleware"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep Demo Queries Available Under Heavy Usage (Priority: P1)

As a developer running a live demo, I need query traffic to be automatically controlled so that one busy session cannot consume all available daily usage and cause the demo to fail for everyone.

**Why this priority**: If quota protection fails, the core demo experience becomes unavailable, which directly breaks the primary business goal of reliable interviews and demos.

**Independent Test**: Can be fully tested by sending controlled request bursts from one and multiple IPs and confirming enforcement behavior without requiring any cache behavior.

**Acceptance Scenarios**:

1. **Given** one IP has made 20 queries within one hour, **When** the same IP sends the 21st query within that hour, **Then** the request is rejected with a per-IP limit error and retry guidance.
2. **Given** total daily query usage has reached the configured daily budget, **When** any IP sends another query, **Then** the request is rejected with a daily quota exhausted error and reset time.

---

### User Story 2 - Serve Common Demo Questions Without Consuming Quota (Priority: P2)

As a developer demoing common topics repeatedly, I want known questions to return pre-cached answers so that I can demonstrate stable behavior even when external AI quota is constrained.

**Why this priority**: Caching protects high-frequency demo paths and lowers the chance of quota-related interruptions during important presentations.

**Independent Test**: Can be fully tested by sending cached and uncached questions to the query endpoints and verifying quota counters and provider-call behavior differ as expected.

**Acceptance Scenarios**:

1. **Given** a query matches one of the ten pre-cached demo questions, **When** the request is processed, **Then** the response is served from cache, streamed incrementally for UX consistency, and does not consume IP or daily quota.
2. **Given** a query does not match a pre-cached question, **When** the request is processed, **Then** the normal answer pipeline runs and daily usage increments by one.

---

### User Story 3 - Monitor Quota Health During Demos (Priority: P3)

As a developer preparing for or running a demo, I want clear quota status and warning signals so that I can proactively adjust usage before hard limits are reached.

**Why this priority**: Visibility reduces surprise failures and enables operators to make informed choices during time-sensitive demos.

**Independent Test**: Can be fully tested by simulating usage levels and verifying status endpoints report accurate counts, percentages, and warning states.

**Acceptance Scenarios**:

1. **Given** known daily usage totals, **When** the quota status endpoint is requested, **Then** it returns accurate used, remaining, percentage-used, and cache hit-rate values.
2. **Given** daily usage is at or above 80% of the configured budget, **When** health status is requested, **Then** quota warning is true while overall health remains available.

### Edge Cases

- What happens when multiple users share the same public IP (for example, office NAT) and collectively hit the hourly cap?
- How does the system behave exactly at daily reset time (midnight UTC) when requests arrive at the boundary?
- How does matching behave for cached questions with different casing, punctuation, or extra spaces?
- What happens when the client IP cannot be reliably determined from request metadata?
- How does the system respond when quota storage is temporarily unavailable while evaluating a request?
- What happens if a client disconnects mid-stream during a cached streaming response?

## Scope Boundaries

### In Scope

- Enforce per-IP hourly query limits.
- Enforce global daily query budget.
- Serve ten predefined demo questions from cache.
- Provide quota status and quota warning visibility.
- Preserve consistent streaming UX for cached streaming responses.

### Out of Scope

- User authentication and per-user quotas.
- Resumable quota windows across multi-day history beyond current daily budget tracking.
- External cache systems or admin dashboards.
- Notification systems for upcoming quota reset.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST enforce a configurable per-IP query limit over a rolling one-hour window for both standard and streaming query requests.
- **FR-002**: System MUST reject requests that exceed the per-IP hourly limit with a clear limit-exceeded response that includes retry timing guidance.
- **FR-003**: System MUST enforce a configurable global daily query budget shared across all IPs.
- **FR-004**: System MUST reject additional query requests after the daily budget is exhausted with a clear daily-quota-exhausted response that includes the next reset time.
- **FR-005**: System MUST maintain a predefined set of ten demo questions with pre-cached answers.
- **FR-006**: System MUST match cacheable questions using normalized text comparison that tolerates case, punctuation, and surrounding whitespace differences.
- **FR-007**: System MUST bypass both per-IP and daily quota consumption for cache-hit requests.
- **FR-008**: System MUST stream cache-hit responses incrementally word-by-word with a default delay of 30 milliseconds per word to preserve interactive UX expectations.
- **FR-009**: System MUST provide a quota status endpoint that returns daily used, limit, remaining, percentage used, warning state, reset timestamp, total cached question count, and daily cache hit rate.
- **FR-010**: System MUST expose quota-warning state in health status when daily usage reaches or exceeds 80% of the configured daily budget, without automatically marking service unavailable solely due to warning level.
- **FR-011**: System MUST support environment-based configuration for hourly limit, daily budget, and cache enable/disable behavior.
- **FR-012**: System MUST preserve current-day global daily usage across service restarts and reset daily usage at midnight UTC.
- **FR-013**: System MUST continue existing non-cached query behavior unchanged for requests that do not match cache entries and do not violate limits.

### Assumptions & Dependencies

- Quota enforcement applies to the existing query endpoints (`/api/v1/query` and `/api/v1/query/stream`) and does not apply to ingestion or evaluation endpoints.
- Per-IP counters are session-memory based and may reset after process restart; persisted continuity is required only for current-day global usage.
- Cache-hit behavior bypasses all quota limits by design to maximize demo reliability.
- Cache-hit streaming simulation uses 30ms word delay as the default UX baseline.
- Daily quota windows reset at midnight UTC.
- Accurate IP-based enforcement depends on reliable client IP resolution from request metadata.

### Key Entities *(include if feature involves data)*

- **IP Quota Window**: Tracks recent request timestamps for one client IP and determines whether another request is allowed in the current hour window.
- **Daily Quota Ledger**: Represents current-day global usage, configured daily limit, remaining budget, percentage used, warning state, and next reset timestamp.
- **Demo Cache Entry**: Represents a normalized demo question and its pre-cached answer content used for deterministic cache hits.
- **Quota Status Snapshot**: Aggregated status payload returned to operators, including daily usage statistics and cache hit-rate metrics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The 21st request from the same IP within one hour is rejected with the expected per-IP limit response in 100% of test runs.
- **SC-002**: After daily usage reaches the configured budget, subsequent requests from any IP are rejected with the expected daily-quota-exhausted response in 100% of test runs.
- **SC-003**: For all ten predefined demo questions, cache-hit requests are served without increasing daily used count and without consuming IP quota in 100% of test runs.
- **SC-004**: Quota status responses report used and remaining counts accurately for controlled traffic scenarios (including the example of 10 used and 290 remaining when limit is 300).
- **SC-005**: Health status includes `quota_warning: true` whenever usage is at or above 80% of configured daily budget, and `quota_warning: false` below that threshold, in 100% of threshold tests.
- **SC-006**: Cached streaming responses deliver first visible content within 1 second and continue incrementally until completion in 95% or more of test runs.

### Performance & UX Targets (if applicable)

- **Page Load**: N/A for backend-only feature.
- **API Performance**: Quota checks add no more than 5ms median processing overhead per request under normal load.
- **Accessibility**: N/A for backend-only feature.
- **Responsive Design**: N/A for backend-only feature.
