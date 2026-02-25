# 006 - Demo Quota Protection Middleware

## Summary
This feature protects live demos from quota exhaustion by combining per-IP limits, daily budget control, and cache bypass for predefined demo questions.

## Key Capabilities
- Per-IP hourly limit (rolling 60-minute window).
- Global daily request budget.
- Pre-cached demo questions that bypass quota usage.
- Quota status visibility endpoint.
- Warning state when daily usage is high.
- Fail-closed behavior when quota storage is unavailable.

## Scope
Applies to query endpoints (`/api/v1/query` and `/api/v1/query/stream`).

## Test Guide
### Automated
```bash
pytest tests -v
```

### Manual Smoke Test
1) Send repeated requests from same IP and verify hourly cap behavior.
2) Hit a cached demo question and verify no quota consumption.
3) Check quota status endpoint fields: used, remaining, warning, reset time.

### Error Cases
- Missing/unresolvable client IP -> HTTP 400.
- Quota storage unavailable -> HTTP 503.

## Success Signals
- Demo remains available under bursty traffic.
- Common demo prompts stay responsive via cache.
- Operators can monitor quota health in real time.
