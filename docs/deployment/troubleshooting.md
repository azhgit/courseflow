# Zeabur Deployment Troubleshooting Guide

## Common Issues and Solutions

### Build and Deployment Issues

#### Build Fails with "ModuleNotFoundError"

**Problem:** Zeabur build fails with `ModuleNotFoundError: No module named 'X'`

**Possible Causes:**
1. Missing dependency in `pyproject.toml`
2. Build command incorrect
3. Python version mismatch

**Solutions:**

1. **Verify dependencies:**
   ```bash
   # Check pyproject.toml has all required packages
   cat pyproject.toml | grep dependencies
   ```

2. **Check build command in zeabur.json:**
   ```json
   {
     "build": {
       "command": "pip install -e ."
     }
   }
   ```

3. **Verify Python version:**
   - Zeabur should auto-detect Python 3.11
   - If not, add `runtime.txt` with `python-3.11`

#### Backend Fails to Start: "ValidationError: GEMINI_API_KEY Field required"

**Problem:** Backend deployment succeeds but service fails to start

**Cause:** Missing `GEMINI_API_KEY` environment variable

**Solution:**
1. Go to Zeabur dashboard → Backend service → Environment Variables
2. Add `GEMINI_API_KEY` with your actual API key
3. Click "Redeploy" button
4. Check logs for successful startup message

#### Frontend Shows "Cannot connect to backend"

**Problem:** Frontend loads but shows connection errors

**Cause:** `VITE_API_BASE_URL` not set or incorrect

**Solution:**
1. Go to Zeabur dashboard → Frontend service → Environment Variables
2. Verify `VITE_API_BASE_URL` is set to backend URL
3. Check URL format: `https://courseflow-backend-xxx.zeabur.app` (no trailing slash)
4. Redeploy frontend
5. Clear browser cache and reload

### CORS Errors

#### "Access-Control-Allow-Origin" Error in Browser Console

**Problem:** Frontend makes request, but browser blocks with CORS error

**Symptoms:**
```
Access to fetch at 'https://backend.zeabur.app/api/v1/query' from origin 
'https://frontend.zeabur.app' has been blocked by CORS policy
```

**Cause:** Backend CORS_ORIGINS doesn't include frontend URL

**Solution:**
1. Go to backend service environment variables
2. Set `CORS_ORIGINS` to include frontend URL:
   ```
   CORS_ORIGINS=https://courseflow-xxx.zeabur.app,http://localhost:5173
   ```
3. **Important:** Use exact frontend URL (copy from Zeabur dashboard)
4. Multiple origins: comma-separated, no spaces
5. Redeploy backend
6. Wait 30 seconds for middleware to reload
7. Test query from frontend

**Verification:**
```bash
# Check CORS headers in response
curl -I -H "Origin: https://courseflow-xxx.zeabur.app" \
  https://courseflow-backend-xxx.zeabur.app/api/v1/health

# Should see:
# access-control-allow-origin: https://courseflow-xxx.zeabur.app
```

### Rate Limiting Issues

#### Rate Limit Triggered Too Easily

**Problem:** Users hit rate limit after only a few requests

**Possible Causes:**
1. Multiple users sharing same IP (corporate proxy)
2. Rate limit too low for testing
3. Rate limit counter not resetting

**Solutions:**

1. **Increase rate limit (temporary for testing):**
   ```
   QUOTA_HOURLY_LIMIT=100
   ```

2. **Check rate limit counter:**
   ```bash
   # On Zeabur, access backend shell
   sqlite3 /app/data/courseflow.db "SELECT * FROM rate_limits;"
   ```

3. **Reset rate limit for IP:**
   ```bash
   # Delete entry to reset
   sqlite3 /app/data/courseflow.db \
     "DELETE FROM rate_limits WHERE ip_address='X.X.X.X';"
   ```

#### Rate Limit Persists After Changing QUOTA_HOURLY_LIMIT

**Problem:** Changed `QUOTA_HOURLY_LIMIT` but users still hit old limit

**Cause:** Existing rate limit entries use old limit

**Solution:**
1. Rate limit entries expire after 1 hour (window resets)
2. To reset immediately:
   ```bash
   # Clear all rate limit counters
   sqlite3 /app/data/courseflow.db "DELETE FROM rate_limits;"
   ```
3. Or wait for natural expiration

### Cold Start Issues

#### Queries Timeout on First Request After Idle

**Problem:** First query after 30+ minutes of inactivity times out

**Cause:** Backend container goes to sleep (cold start)

**Expected Behavior:**
- Cold start delay: 5-15 seconds
- Frontend retry logic should handle this automatically
- After 3 retries (1s, 2s, 4s delays), shows error

**Solutions:**

1. **Verify retry logic is working:**
   - Check browser DevTools Console
   - Should see retry attempts logged
   - Final error after ~7 seconds total

2. **Keep backend warm (optional):**
   - Set up uptime monitor (UptimeRobot, etc.)
   - Ping health check every 5 minutes:
     ```
     */5 * * * * curl https://courseflow-backend-xxx.zeabur.app/api/v1/health
     ```

3. **Increase frontend timeout:**
   - Edit `src/frontend/src/api/client.js`
   - Increase timeout from 10s to 20s (not recommended)

### Database Issues

#### "database is locked" Error

**Problem:** Backend logs show `OperationalError: database is locked`

**Cause:** SQLite doesn't handle high concurrency well

**Solutions:**

1. **Reduce concurrent requests:**
   - Rate limiting already helps with this
   - Ensure `QUOTA_HOURLY_LIMIT` is reasonable (20-50)

2. **Add retry logic for database operations:**
   - Already implemented in repository layer
   - Check logs for retry attempts

3. **If persistent, consider upgrade:**
   - Zeabur Free Trial limits may be reached
   - Consider PostgreSQL for production (requires paid plan)

#### ChromaDB Data Missing After Deployment

**Problem:** Backend starts but queries return "no documents found"

**Cause:** ChromaDB data not persisted in deployment

**Solutions:**

1. **Verify ChromaDB directory exists:**
   ```bash
   # In backend container
   ls -la /app/data/chroma
   ```

2. **Check if data is committed to Git:**
   ```bash
   git status
   # data/chroma/ should be tracked (not in .gitignore)
   ```

3. **Re-ingest documents:**
   - Use ingestion API endpoint
   - Or re-deploy with ChromaDB data included

### Auto-Deploy Issues

#### GitHub Push Doesn't Trigger Deployment

**Problem:** Pushed code to `main` branch but Zeabur didn't redeploy

**Solutions:**

1. **Verify webhook exists:**
   - GitHub repo → Settings → Webhooks
   - Should see webhook with `zeabur.com` URL
   - Check "Recent Deliveries" tab
   - Recent push should show HTTP 200 response

2. **Check webhook events:**
   - Webhook should listen for `push` events
   - Verify branch filter (should include `main`)

3. **Manually trigger redeploy:**
   - Zeabur dashboard → Service → "Redeploy" button

4. **Re-link repository:**
   - Zeabur dashboard → Service settings
   - Disconnect and reconnect GitHub repository
   - Webhook will be recreated

#### Deployment Stuck in "Building" State

**Problem:** Deployment shows "Building..." for >10 minutes

**Possible Causes:**
1. Build step hanging (waiting for input)
2. Network issue downloading dependencies
3. Build timeout exceeded

**Solutions:**

1. **Check build logs:**
   - Zeabur dashboard → Service → Logs
   - Look for errors or last successful step

2. **Cancel and retry:**
   - Click "Cancel Build"
   - Click "Redeploy"

3. **Check build command:**
   - Ensure build command doesn't require interactive input
   - Example: `pip install -e .` should not prompt

### Health Check Failures

#### Health Check Returns 503 "degraded"

**Problem:** Health check endpoint returns HTTP 503

**Cause:** One or more components unhealthy

**Solution:**
1. Check health check response:
   ```bash
   curl https://courseflow-backend-xxx.zeabur.app/api/v1/health | jq
   ```

2. Identify unhealthy component:
   ```json
   {
     "status": "degraded",
     "components": {
       "chromadb": {"status": "error", "message": "..."},
       "sqlite": {"status": "ok"},
       "gemini_api": {"status": "ok"}
     }
   }
   ```

3. Fix specific component:
   - **ChromaDB error:** Check data directory exists
   - **SQLite error:** Check database file permissions
   - **Gemini API error:** Verify API key, check quota

#### Health Check Times Out

**Problem:** Health check request times out (>30 seconds)

**Cause:** Backend not responding (crashed or overloaded)

**Solutions:**

1. **Check if backend is running:**
   - Zeabur dashboard → Backend service
   - Status should be "Running"

2. **Check backend logs:**
   - Look for errors, crashes, or OOM (out of memory)

3. **Restart backend:**
   - Zeabur dashboard → "Restart" button

4. **Check memory usage:**
   - Free Trial: 512MB limit
   - If exceeded, optimize code or upgrade plan

### Performance Issues

#### Queries Are Slow (>10 seconds)

**Problem:** E2E query time exceeds 10 seconds consistently

**Possible Causes:**
1. Gemini API slow response
2. Too many ChromaDB documents
3. Network latency

**Solutions:**

1. **Check component latencies:**
   ```bash
   curl https://backend.zeabur.app/api/v1/health | jq '.components'
   ```

2. **Optimize ChromaDB:**
   - Reduce `TOP_K_RESULTS` from 3 to 2
   - Increase `SIMILARITY_THRESHOLD` from 0.5 to 0.6

3. **Check Gemini API status:**
   - Visit [Google Cloud Status](https://status.cloud.google.com/)
   - Verify no ongoing incidents

#### Frontend Load Time >5 Seconds

**Problem:** Frontend takes >5 seconds to load initially

**Cause:** Unoptimized build or slow CDN

**Solutions:**

1. **Verify build optimization:**
   ```bash
   # Check build output
   npm run build
   # Should show minification and tree-shaking
   ```

2. **Check bundle size:**
   ```bash
   cd src/frontend && ls -lh dist/*.js
   # Main bundle should be <500KB
   ```

3. **Enable Vite optimizations:**
   ```javascript
   // vite.config.js
   export default {
     build: {
       minify: 'terser',
       rollupOptions: {
         output: {
           manualChunks: {
             vendor: ['react', 'react-dom']
           }
         }
       }
     }
   }
   ```

### Zeabur-Specific Issues

#### Free Trial Credit Exhausted

**Problem:** Services stop after a few days

**Cause:** $5 Free Trial credit used up

**Solutions:**

1. **Monitor credit usage:**
   - Zeabur dashboard → Project → Usage tab

2. **Optimize costs:**
   - Reduce instance size (already at minimum)
   - Stop services when not in use
   - Use uptime monitoring sparingly

3. **Upgrade to paid plan:**
   - Required for longer-term deployments
   - Pay-as-you-go pricing

#### PORT Environment Variable Not Working

**Problem:** Backend doesn't bind to correct port

**Cause:** Zeabur sets `PORT` dynamically, but code ignores it

**Solution:**
1. Verify Dockerfile CMD uses `$PORT`:
   ```dockerfile
   CMD uvicorn src.courseflow.api.main:app --host 0.0.0.0 --port ${PORT}
   ```

2. Or in zeabur.json:
   ```json
   {
     "start": {
       "command": "uvicorn src.courseflow.api.main:app --host 0.0.0.0 --port $PORT"
     }
   }
   ```

3. Check Zeabur logs:
   ```
   # Should see:
   Uvicorn running on http://0.0.0.0:8080
   ```

## Debugging Techniques

### Viewing Logs

**Backend logs:**
```bash
# Via Zeabur dashboard
Zeabur → Backend service → Logs tab → Filter by level

# Recent errors
Zeabur → Logs → Filter: "ERROR"
```

**Frontend logs:**
- Frontend is static (no server logs)
- Use browser DevTools Console

### Testing Locally

Before deploying, test locally:

```bash
# Backend
cd /path/to/CourseFlow
export GEMINI_API_KEY=your_key
python -m uvicorn src.courseflow.api.main:app --reload

# Frontend
cd src/frontend
npm install
npm run dev
```

### Testing Rate Limiting Locally

```bash
# Set low limit for testing
export QUOTA_HOURLY_LIMIT=5

# Run backend
python -m uvicorn src.courseflow.api.main:app

# Test in another terminal
for i in {1..6}; do
  echo "Request $i:"
  curl -X POST http://localhost:8000/api/v1/query \
    -H "Content-Type: application/json" \
    -d '{"query": "test"}' \
    -w "\nHTTP Status: %{http_code}\n\n"
done
```

## Getting Help

If issues persist after trying solutions above:

1. **Check Zeabur Status:**
   - [Zeabur Status Page](https://status.zeabur.com)

2. **Zeabur Documentation:**
   - [Zeabur Docs](https://zeabur.com/docs)

3. **CourseFlow Issues:**
   - GitHub Issues (if repository is public)
   - Contact maintainers

4. **Community Support:**
   - Zeabur Discord
   - Stack Overflow (tag: zeabur, fastapi, react)

## Preventive Measures

### Before Deployment Checklist

- [ ] All environment variables documented
- [ ] `.env.example` files up to date
- [ ] Health check endpoint tested locally
- [ ] Rate limiting tested with 21+ requests
- [ ] CORS origins include production URL
- [ ] ChromaDB data committed to Git
- [ ] Build succeeds locally (`npm run build`, `pip install -e .`)
- [ ] Dockerfile tested locally (`docker build -t courseflow .`)

### Monitoring Setup

1. **Uptime monitoring:**
   - Set up UptimeRobot or similar
   - Monitor health check endpoint
   - Alert on >2 minute downtime

2. **Error tracking:**
   - Optional: Sentry for frontend/backend errors
   - Track rate limit violations
   - Track cold start frequency

3. **Usage monitoring:**
   - Zeabur dashboard credit usage
   - Gemini API quota usage (Google Cloud Console)
   - SQLite database size growth

### Regular Maintenance

**Weekly:**
- Check Zeabur credit usage
- Review error logs
- Verify auto-deploy still working (test with minor commit)

**Monthly:**
- Clean up old rate_limit entries:
  ```sql
  DELETE FROM rate_limits WHERE last_request < datetime('now', '-7 days');
  ```
- Review and rotate API keys
- Update dependencies (security patches)

## Quick Reference

### Essential Commands

```bash
# Health check
curl https://backend.zeabur.app/api/v1/health

# Test query
curl -X POST https://backend.zeabur.app/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Python?"}'

# Check rate limit
curl -I https://backend.zeabur.app/api/v1/query \
  | grep X-RateLimit

# Clear rate limits
sqlite3 /app/data/courseflow.db "DELETE FROM rate_limits;"
```

### Environment Variables Quick Reference

**Required:**
- Backend: `GEMINI_API_KEY`
- Frontend: `VITE_API_BASE_URL`

**Recommended:**
- Backend: `CORS_ORIGINS` (set to frontend URL)
- Backend: `QUOTA_HOURLY_LIMIT=20`

**Optional:**
- Backend: `LOG_LEVEL=INFO`
- Backend: `RATE_LIMIT_RPM=15`

### URL Patterns

- Backend: `https://courseflow-backend-[id].zeabur.app`
- Frontend: `https://courseflow-[id].zeabur.app`
- Health check: `/api/v1/health`
- Query endpoint: `/api/v1/query`
