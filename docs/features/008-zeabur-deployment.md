# 008 - Zeabur Deployment

## Summary
This feature makes CourseFlow publicly accessible via Zeabur and supports automatic redeploy on Git push.

## Key Capabilities
- Deploy backend (FastAPI container) and frontend (static React) on Zeabur.
- Public URLs for interview/demo access.
- Auto-redeploy workflow on main-branch updates.
- Environment-variable-based configuration for API URL and secrets.
- CORS configured for deployed frontend origin.
- Demo-oriented rate limiting and health checks.

## Deployment Scope
- Backend service: API + health endpoint.
- Frontend service: static build served publicly.
- GitHub integration: trigger rebuild on push.

## Test Guide
### Deployment Verification
- Frontend URL loads successfully.
- Backend `GET /api/v1/health` returns HTTP 200.
- Frontend-to-backend query flow works without CORS errors.

### Auto-Redeploy Verification
1) Push a harmless change to main.
2) Confirm Zeabur rebuild starts.
3) Confirm new version becomes live.

### Rate-Limit Verification
- Send requests beyond configured threshold and expect HTTP 429.

## Success Signals
- Portfolio/demo links are stable and accessible.
- Deployments are reproducible and low-touch.
- Operational issues are diagnosable from platform logs.
