# Feature Specification: Zeabur Deployment

**Feature Branch**: `008-zeabur-deployment`  
**Created**: 2026-02-17  
**Status**: Clarified  
**Input**: Production deployment on Zeabur with auto-redeploy on git push

## User Scenarios & Testing

### User Story 1 - Deploy for Interview (Priority: P1)

As an internship candidate, I want the CourseFlow application deployed at public URLs so interviewers can test it directly without local setup, enabling a stronger live demo impression than a laptop presentation.

**Why this priority**: Core business need — enables portfolio presentation and live technical evaluation by interviewers.

**Independent Test**: Deployment is complete when both URLs are publicly accessible and the frontend can successfully query the backend (verified by submitting a question and receiving a streaming response).

**Acceptance Scenarios**:

1. **Given** Zeabur Free Trial project is created, **When** backend and frontend services are deployed, **Then** both services receive unique public URLs (e.g., `https://courseflow-api.zeabur.app` and `https://courseflow.zeabur.app`)
2. **Given** public URL is shared via resume/portfolio link, **When** an interviewer opens the URL in a browser, **Then** React frontend loads within 3 seconds without console errors
3. **Given** frontend is loaded and ready, **When** user submits a question from the chat interface, **Then** streaming response arrives from the backend without CORS errors
4. **Given** both services are deployed, **When** a health check request is made to `/api/v1/health`, **Then** HTTP 200 is returned with `{"status": "healthy"}` from any network

---

### User Story 2 - Auto-Redeploy on Push (Priority: P1)

As a developer iterating on the feature, I want changes to automatically redeploy when I push to the main branch, so I don't need to manually trigger builds and can iterate rapidly during development.

**Why this priority**: Core developer experience — eliminates manual deployment steps and accelerates feedback loops.

**Independent Test**: Can be tested by committing a minor code change (e.g., version bump) to main and verifying that Zeabur detects the push, triggers a rebuild, and deploys the new version within 5 minutes.

**Acceptance Scenarios**:

1. **Given** code is pushed to the main branch, **When** GitHub webhook is triggered, **Then** Zeabur automatically starts a rebuild
2. **Given** rebuild is in progress, **When** build completes successfully, **Then** new version is live and accessible at the public URL within 5 minutes total
3. **Given** multiple pushes occur in sequence, **When** each push triggers a rebuild, **Then** only the latest build is deployed (earlier builds are cancelled or superseded)

---

### User Story 3 - Rate Limit Protection (Priority: P2)

As a platform provider, I want demo quota protection to prevent interviewers from exhausting API rates during presentation, ensuring the demo remains stable throughout the interview session.

**Why this priority**: Risk mitigation — prevents bad user experience during critical evaluation moment.

**Independent Test**: Can be tested by sending 21 consecutive requests from a single IP address and verifying that the 21st request returns HTTP 429 with rate limit error.

**Acceptance Scenarios**:

1. **Given** demo rate limit is set to 20 requests per hour, **When** 20 requests are submitted from the same IP, **Then** all requests succeed with HTTP 200
2. **Given** rate limit has been reached, **When** the 21st request is attempted from the same IP, **Then** HTTP 429 is returned with appropriate error message
3. **Given** an hour has passed since the limit was reached, **When** a new request is made from the same IP, **Then** the rate limit counter resets and requests succeed again

---

### Edge Cases

- **Cold start delay**: After idle period, container may take up to 30 seconds to start. Frontend implements automatic retry logic with exponential backoff (1s, 2s, 4s delays, max 3 attempts) to handle startup delays gracefully.
- **Database reset on redeploy**: SQLite rate limit counters persist across container restarts (stored separately from transient demo data).
- **ChromaDB data in repo**: Knowledge base is committed to version control; large file size may impact clone performance.
- **Environment variable misconfiguration**: If backend URL is incorrect in frontend env vars (VITE_API_URL), CORS requests will fail; frontend retry logic will exhaust and display user-friendly error message.
- **API key expiration**: If Gemini API key expires or quota is exhausted, backend returns 503; frontend displays friendly error message after retry exhaustion.
- **Zeabur service outage**: If Zeabur experiences downtime, demo is unavailable; no SLA guaranteed for free tier.

## Requirements

### Functional Requirements

- **FR-001**: System MUST deploy FastAPI backend as containerized service on Zeabur with auto-scaling disabled (single instance for demo stability).
- **FR-002**: System MUST deploy React frontend as static site service on Zeabur with caching enabled.
- **FR-003**: Both services MUST be in the same Zeabur project and share resource limits under the Free Trial ($0/month with $5 credit).
- **FR-004**: Backend MUST bind to the `$PORT` environment variable set by Zeabur (default 3000).
- **FR-005**: Frontend build output MUST be pure static files (HTML, CSS, JS, assets) with no server-side rendering.
- **FR-006**: Backend MUST accept frontend requests from `https://courseflow.zeabur.app` only (CORS configured to prevent cross-origin attacks).
- **FR-007**: System MUST support additional localhost origins (`http://localhost:5173`) for local development without affecting production config.
- **FR-007a**: Frontend MUST read backend API URL from build-time environment variable (VITE_API_URL) injected during npm run build; supports separate dev/prod builds without code changes.
- **FR-008**: Backend MUST implement HTTP 429 rate limiting at 20 requests per hour per IP address via middleware with SQLite persistence across container restarts.
- **FR-009**: All environment variables (API keys, database URLs, rate limits) MUST be configured via Zeabur dashboard, never committed to code.
- **FR-010**: System MUST automatically redeploy when commits are pushed to the main branch; Zeabur auto-configures GitHub webhook when repository is linked (no manual setup required).
- **FR-011**: Backend health check endpoint (`/api/v1/health`) MUST return HTTP 200 with component status without requiring authentication.
- **FR-012**: ChromaDB knowledge base (`data/chroma/`) MUST be committed to the repository and included in the deployed container.
- **FR-013**: SQLite database file (`data/courseflow.db`) is ephemeral and resets on each redeploy (no persistent storage required for demo).
- **FR-014**: Frontend MUST implement automatic retry logic with exponential backoff (max 3 attempts, 1s/2s/4s delays) for handling backend cold start delays and transient failures.
- **FR-015**: Zeabur dashboard MUST provide accessible logs via browser UI for debugging deployment issues and request errors.

### Key Entities

- **Zeabur Service (Backend)**: Containerized FastAPI application with 1 vCPU, 512MB memory, connected to Gemini API; rate limit counters stored in SQLite.
- **Zeabur Service (Frontend)**: Static React build served via CDN, connected to backend via VITE_API_URL environment variable; implements client-side retry logic.
- **GitHub Repository**: Source of truth for code and data; auto-configured webhook triggers Zeabur rebuilds on main branch pushes.
- **Gemini API Key**: Environment variable injected at runtime; rate-limited to 15 RPM by Gemini free tier.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Frontend loads from public URL within 3 seconds (measured via browser DevTools; P95 latency).
- **SC-002**: Health check endpoint returns HTTP 200 from any public network within 1 second of deployment startup.
- **SC-003**: End-to-end query (submit question → receive streaming response) completes within 8 seconds from user submission to first token received.
- **SC-004**: Rate limiting is active: 20 requests per hour per IP returns HTTP 200; 21st request returns HTTP 429.
- **SC-005**: Auto-redeploy completes within 5 minutes of git push to main branch.
- **SC-006**: Cold start (container startup after idle) handled gracefully: frontend retry logic succeeds or displays user-friendly error within 12 seconds.
- **SC-007**: Both public URLs are shareable in resume/portfolio and accessible without login for at least 30 days (duration of internship interview period).
- **SC-008**: No CORS errors in browser console when submitting questions from frontend to backend.
- **SC-009**: Rate limit counters persist across container restarts (verified by redeploying and confirming counter state preserved).

### Performance & UX Targets

- **Page Load**: Frontend loads in <3 seconds on standard 4G/WiFi (measured via Lighthouse or browser DevTools).
- **API Performance**: Backend health check responds in <1s; RAG query responses stream results in <8s from submission.
- **Retry Behavior**: Frontend retry logic with exponential backoff (3 attempts, 1/2/4s delays) handles up to 7 seconds of backend unavailability.
- **Availability**: Free Trial tier; no SLA guaranteed; assumes <10 concurrent users during demo.

## Assumptions

- **Zeabur Free Trial eligibility**: Account qualifies for free tier with $5 monthly credit.
- **GitHub integration**: Zeabur will auto-configure GitHub webhook when repository is linked; no manual webhook setup required.
- **Build-time env vars**: Zeabur build system supports VITE_API_URL injection during npm run build for frontend.
- **SQLite rate limit storage**: Backend can store rate limit counters in SQLite (survives container restarts).
- **Frontend retry logic**: Frontend implements exponential backoff with 3 maximum retries (1s, 2s, 4s delays) for handling cold starts and transient failures.
- **Zeabur dashboard logging**: Zeabur dashboard provides sufficient log access via browser UI for demo troubleshooting.
- **No custom domain**: Uses `zeabur.app` subdomain; custom domain setup is out of scope.
- **SSL/TLS**: Zeabur provides automatic HTTPS certificates; no manual setup required.
- **ChromaDB committed to repo**: Pre-built knowledge base included in version control (no dynamic ingestion during deployment).
- **Demo runs <30 days**: Internship interview period is the expected duration; no long-term maintenance required.
- **Single instance**: No load balancing or multi-region deployment; acceptable for low-traffic demo.

## Dependencies & Constraints

**Internal Dependencies**:
- Requires completed FastAPI backend from Feature 001 (RAG QA system).
- Requires completed React frontend from Feature 007 (React frontend MVP).
- Depends on pre-loaded ChromaDB knowledge base (Feature 001 ingestion complete).

**External Dependencies**:
- Zeabur Free Trial account and project setup.
- GitHub account with CourseFlow repository access.
- Gemini API key with valid quota (15 RPM free tier).

**Technical Constraints**:
- **Memory**: 512MB per service (Zeabur Free Trial limit); backend must fit within limit including ChromaDB and FastAPI runtime.
- **CPU**: 1 vCPU per service; no horizontal scaling on free tier.
- **Storage**: 2GB ephemeral container storage; ChromaDB persistence is local, reset on redeploy.
- **Bandwidth**: Zeabur free tier includes reasonable bandwidth; no explicit limit for demo use.
- **Build time**: Builds must complete within Zeabur timeout (typically 15-20 minutes).

## Out of Scope (Explicitly)

- Custom domain (zeabur.app subdomain is sufficient).
- SSL certificate setup (Zeabur handles automatically).
- Database backups or persistent storage (ephemeral acceptable for demo).
- Multi-region deployment.
- Load balancing or auto-scaling.
- CI/CD beyond auto-deploy on push.
- Staging environment separate from production.
- Analytics or monitoring dashboards.
- Secrets rotation or management beyond Zeabur dashboard.

## Notes

- **Constitution Alignment**: Uses Zeabur Free Trial ($0/month + $5 credit) — maintains zero-cost constraint; no paid cloud hosting required.
- **Interview Readiness**: Feature enables live demo with interviewers; critical for portfolio/interview presentation value.
- **Clarifications Resolved**:
  - Frontend URL discovery: Build-time VITE_API_URL injection (supports dev/prod environment separation without code changes)
  - Rate limiting: Backend middleware with SQLite persistence (survives container restarts)
  - GitHub webhook: Auto-configured by Zeabur (zero manual setup; no user intervention required)
  - Cold start UX: Frontend retry logic with exponential backoff (3 attempts, 1/2/4s delays; graceful user-friendly error display)
  - Observability: Zeabur dashboard logs accessible via browser (sufficient for demo troubleshooting; no external tools required)
