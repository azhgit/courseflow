# Zeabur Deployment Quickstart

**Feature**: 008-zeabur-deployment  
**Target**: CourseFlow backend + frontend deployment  
**Platform**: Zeabur Free Trial  
**Estimated Time**: 30 minutes

---

## Prerequisites

Before starting, ensure you have:

- [ ] **Zeabur Free Trial Account**: Sign up at [zeabur.com](https://zeabur.com) (GitHub OAuth)
- [ ] **GitHub Repository Access**: Admin or write access to CourseFlow repository
- [ ] **Gemini API Key**: Free tier from [Google AI Studio](https://makersuite.google.com/app/apikey)
- [ ] **Git Branch**: Ensure `main` branch has latest code from Features 001 (backend) and 007 (frontend)

---

## Step 1: Create Zeabur Project

1. **Log in to Zeabur**:
   - Navigate to [Zeabur Dashboard](https://zeabur.com)
   - Click "Sign in with GitHub"

2. **Create New Project**:
   - Click "+ New Project" button
   - Project name: `courseflow-demo` (or your preference)
   - Region: Select closest to your location (e.g., `us-west-1`)
   - Plan: **Free Trial** (automatically selected, includes $5 credit)

3. **Verify Project Created**:
   - Project dashboard should appear
   - Note: Free Trial includes 512MB RAM, 1 vCPU per service

---

## Step 2: Deploy Backend Service

### 2.1 Add Git Repository Service

1. In project dashboard, click **"Add Service"**
2. Select **"Git Repository"**
3. Authorize Zeabur to access your GitHub account (if first time)
4. Select repository: `CourseFlow`
5. Select branch: `main`

### 2.2 Configure Backend Service

**Service Settings**:
- **Service Name**: `courseflow-backend`
- **Root Directory**: `/backend` (important: frontend and backend are separate services)
- **Framework Detection**: Zeabur should auto-detect Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn src.courseflow.api.main:app --host 0.0.0.0 --port $PORT`

**Port Binding Note**: `$PORT` is injected by Zeabur dynamically (typically 3000-5000). Do NOT hardcode port.

### 2.3 Add Environment Variables

In backend service settings → **Environment Variables** tab, add:

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `GEMINI_API_KEY` | `<your-api-key>` | Gemini API key from Google AI Studio |
| `CORS_ORIGINS` | `https://courseflow-frontend.zeabur.app,http://localhost:5173` | Allowed CORS origins (update frontend URL after deployment) |
| `RATE_LIMIT_PER_HOUR` | `20` | Rate limit threshold (requests per hour per IP) |
| `DATABASE_URL` | `sqlite:///./data/courseflow.db` | SQLite database path (ephemeral) |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | ChromaDB persistence directory |

**Important**: Copy **exact backend URL** from Zeabur dashboard after deployment (format: `https://courseflow-backend-<unique-id>.zeabur.app`). You'll need this for frontend configuration.

### 2.4 Deploy Backend

1. Click **"Deploy"** button
2. Wait for build to complete (~2-3 minutes)
3. Monitor logs in **"Logs"** tab for errors
4. Verify deployment success: Green checkmark + "Running" status

### 2.5 Test Backend Health Check

```bash
curl https://courseflow-backend-<your-id>.zeabur.app/api/v1/health
```

**Expected Response** (HTTP 200):
```json
{
  "status": "healthy",
  "timestamp": "2025-02-17T12:34:56Z",
  "components": {
    "database": "ok",
    "vector_store": "ok",
    "llm_api": "ok"
  }
}
```

**If health check fails**, see [Troubleshooting](#troubleshooting) section.

---

## Step 3: Deploy Frontend Service

### 3.1 Add Second Git Repository Service

1. In same project, click **"Add Service"** again
2. Select **"Git Repository"**
3. Select same repository: `CourseFlow`
4. Select branch: `main`

### 3.2 Configure Frontend Service

**Service Settings**:
- **Service Name**: `courseflow-frontend`
- **Root Directory**: `/frontend` (separate from backend)
- **Framework Detection**: Zeabur should auto-detect Node.js/Vite
- **Build Command**: `npm install && npm run build`
- **Output Directory**: `dist` (Vite default build output)
- **Service Type**: **Static Site** (important for CDN deployment)

### 3.3 Add Environment Variables

In frontend service settings → **Environment Variables** tab, add:

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `VITE_API_URL` | `https://courseflow-backend-<your-id>.zeabur.app` | Backend API base URL (copy exact URL from Step 2.3) |

**Critical**: The backend URL MUST match exactly (no trailing slash). Frontend build reads `VITE_API_URL` at build time and bakes it into static files.

### 3.4 Deploy Frontend

1. Click **"Deploy"** button
2. Wait for build to complete (~1-2 minutes)
3. Monitor logs for build errors
4. Verify deployment success: Green checkmark + "Running" status

### 3.5 Test Frontend

1. Open frontend URL in browser: `https://courseflow-frontend-<your-id>.zeabur.app`
2. Verify:
   - Page loads within 3 seconds
   - No console errors (open DevTools → Console)
   - Chat interface is visible

3. **Test End-to-End Query**:
   - Submit question: "What is async/await in Python?"
   - Verify streaming response appears (should take <8 seconds)
   - Check browser Network tab for CORS errors (should be none)

---

## Step 4: Configure Auto-Deploy

Zeabur automatically configures GitHub webhook when repository is linked. Verify webhook setup:

### 4.1 Verify GitHub Webhook

1. Go to GitHub repository: `CourseFlow`
2. Navigate to **Settings** → **Webhooks**
3. Look for webhook with URL containing `zeabur.com`
4. Verify:
   - **Payload URL**: `https://webhook.zeabur.com/...`
   - **Content type**: `application/json`
   - **Events**: `push` to `main` branch
   - **Active**: ✅ (green checkmark)

**If webhook is missing**: Re-link repository in Zeabur project settings.

### 4.2 Test Auto-Deploy

1. Make a minor code change (e.g., update version in `package.json`)
2. Commit and push to `main` branch:
   ```bash
   git add .
   git commit -m "test: Verify auto-deploy"
   git push origin main
   ```
3. Check Zeabur dashboard → **Deployments** tab
4. Verify:
   - New deployment triggered within 30 seconds
   - Build completes successfully
   - New version deployed within 5 minutes total

---

## Step 5: Final Verification

Run all success criteria tests to verify deployment:

### SC-001: Frontend Load Time

```bash
# Measure page load time
curl -o /dev/null -s -w 'Total time: %{time_total}s\n' \
  https://courseflow-frontend-<your-id>.zeabur.app
```

**Expected**: <3 seconds (P95)

### SC-002: Health Check Response Time

```bash
# Measure health check latency
curl -o /dev/null -s -w 'Health check time: %{time_total}s\n' \
  https://courseflow-backend-<your-id>.zeabur.app/api/v1/health
```

**Expected**: <1 second

### SC-003: End-to-End Query

1. Open frontend in browser
2. Open DevTools → Network tab → Record
3. Submit question: "What is photosynthesis?"
4. Measure time from submission to first token in response
5. **Expected**: <8 seconds

### SC-004: Rate Limit Enforcement

```bash
# Send 21 consecutive requests
for i in {1..21}; do
  echo "Request $i:"
  curl -w "\nHTTP Status: %{http_code}\n" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"query": "test"}' \
    https://courseflow-backend-<your-id>.zeabur.app/api/v1/query
done
```

**Expected**: 
- Requests 1-20: HTTP 200
- Request 21: HTTP 429 (Too Many Requests) with `Retry-After` header

### SC-005: Auto-Redeploy Time

1. Push commit to `main` branch
2. Note timestamp: `git log -1 --format=%ci`
3. Wait for Zeabur deployment to complete
4. Check new version live: `curl <frontend-url> | grep version`
5. Calculate: Live time - Commit time
6. **Expected**: <5 minutes

### SC-006: Cold Start Handling

1. Leave frontend idle for 30 minutes (backend container may sleep)
2. Submit query from frontend
3. Observe frontend behavior:
   - Should show "Backend starting up... Retry attempt 1/3"
   - Should retry with exponential backoff (1s, 2s, 4s)
   - Should succeed OR show user-friendly error within 12 seconds
4. **Expected**: Success or graceful error, no crash

### SC-008: No CORS Errors

1. Open frontend in browser
2. Open DevTools → Console
3. Submit query
4. **Expected**: Zero CORS-related errors in console

### SC-009: Rate Limit Persistence

1. Submit 15 requests to backend (note: within rate limit)
2. Redeploy backend service (trigger rebuild in Zeabur dashboard)
3. After redeployment, submit 6 more requests
4. **Expected**: 21st total request returns HTTP 429 (counter persisted across restart)

---

## Step 6: Share Public URLs

Your deployment is now live! Share these URLs:

- **Frontend**: `https://courseflow-frontend-<your-id>.zeabur.app`
- **Backend Health Check**: `https://courseflow-backend-<your-id>.zeabur.app/api/v1/health`

**Recommended for Resume/Portfolio**:
- Use a custom URL shortener (e.g., Bitly) for cleaner links
- Add to resume: "Live Demo: bit.ly/courseflow-demo"
- Include in GitHub README with screenshots

---

## Troubleshooting

### Backend Health Check Returns 503

**Symptoms**: `/api/v1/health` returns HTTP 503 or "degraded" status

**Possible Causes**:
1. **Missing Gemini API Key**: Check environment variable `GEMINI_API_KEY` is set
2. **ChromaDB Not Found**: Verify `data/chroma/` directory exists in backend container
3. **SQLite Permission Error**: Check container has write access to `data/` directory

**Solutions**:
1. Verify all environment variables in Zeabur dashboard
2. Check backend logs: Zeabur dashboard → Backend service → **Logs** tab
3. Rebuild backend: Click "Redeploy" button

### Frontend Shows "Backend Unavailable" Error

**Symptoms**: Frontend loads but queries fail with error message

**Possible Causes**:
1. **Wrong VITE_API_URL**: Frontend pointing to incorrect backend URL
2. **CORS Error**: Backend not allowing frontend origin
3. **Backend Down**: Health check failing

**Solutions**:
1. Verify `VITE_API_URL` matches exact backend URL (no trailing slash)
2. Verify `CORS_ORIGINS` in backend includes exact frontend URL
3. Test health check: `curl <backend-url>/api/v1/health`
4. Check browser console for CORS errors (red text with "CORS")
5. Rebuild frontend after fixing `VITE_API_URL`

### CORS Errors in Browser Console

**Symptoms**: Browser console shows "Access-Control-Allow-Origin" errors

**Possible Causes**:
1. **Backend CORS_ORIGINS Mismatch**: Frontend URL not in backend's allowed origins
2. **Protocol Mismatch**: Mixing HTTP and HTTPS

**Solutions**:
1. Update backend `CORS_ORIGINS` environment variable:
   ```
   CORS_ORIGINS=https://courseflow-frontend-<your-id>.zeabur.app,http://localhost:5173
   ```
2. Ensure both URLs use HTTPS (Zeabur auto-provides SSL)
3. Redeploy backend after updating `CORS_ORIGINS`

### Rate Limiting Not Working (21st Request Succeeds)

**Symptoms**: Can send >20 requests without getting HTTP 429

**Possible Causes**:
1. **SQLite Database Not Persisting**: Container storage ephemeral
2. **Rate Limiter Middleware Not Registered**: Code issue

**Solutions**:
1. Check backend logs for rate limiter initialization
2. Verify `rate_limits` table exists: Connect to SQLite and run `SELECT * FROM rate_limits;`
3. Test with same IP: Send requests from single machine/network

### Auto-Deploy Not Triggering

**Symptoms**: Pushing to `main` branch doesn't trigger Zeabur rebuild

**Possible Causes**:
1. **GitHub Webhook Missing or Inactive**: Zeabur didn't configure webhook
2. **Wrong Branch**: Pushing to non-`main` branch

**Solutions**:
1. Verify webhook: GitHub repo → Settings → Webhooks → Check for `zeabur.com` webhook
2. Re-link repository: Zeabur dashboard → Service settings → "Reconnect Git Repository"
3. Manual trigger: Zeabur dashboard → Service → "Redeploy" button

### Build Timeout After 15 Minutes

**Symptoms**: Build fails with "Timeout" error

**Possible Causes**:
1. **Slow Dependency Installation**: Large ChromaDB or npm packages
2. **Incorrect Build Command**: Command hangs or loops

**Solutions**:
1. Check build logs for stuck command
2. Optimize build: Remove unused dependencies, use `--no-cache` for pip/npm
3. Contact Zeabur support for build timeout extension (unlikely needed)

### ChromaDB Data Missing After Deployment

**Symptoms**: Queries return "No documents found"

**Possible Causes**:
1. **ChromaDB Not Committed to Repo**: `data/chroma/` directory gitignored
2. **Container Storage Reset**: Ephemeral storage lost

**Solutions**:
1. Verify `data/chroma/` exists in GitHub repository (should be committed for deployment)
2. If missing, run ingestion script locally and commit:
   ```bash
   python scripts/ingest_docs.py
   git add -f data/chroma/
   git commit -m "feat: Add ChromaDB data for deployment"
   git push origin main
   ```

---

## Monitoring & Observability

### Zeabur Dashboard Logs

Access logs for debugging:
1. Zeabur dashboard → Select service (backend or frontend)
2. Click **"Logs"** tab
3. View real-time logs (auto-scrolls)
4. Filter by log level: Info, Warning, Error

**Log Retention**: Zeabur Free Trial keeps logs for 7 days.

### Health Check Monitoring

Set up external monitoring (optional):
1. Use [UptimeRobot](https://uptimerobot.com) (free tier)
2. Add monitor: Type = HTTP(s), URL = `<backend-url>/api/v1/health`
3. Check interval: 5 minutes
4. Alert on HTTP status != 200

### Metrics Endpoint (Future)

Implement `/metrics` endpoint for Prometheus scraping (out of scope for Feature 008).

---

## Cost Monitoring

### Zeabur Free Trial Usage

- **Credit Balance**: $5 total (non-renewable on free tier)
- **Usage Dashboard**: Zeabur → Billing → Usage
- **Expected Consumption**: ~$0.50/month for 2 services (backend + frontend)

**Action Items**:
- Monitor usage weekly
- If credit exhausted, upgrade to paid plan ($5/month minimum)
- Set up billing alerts in Zeabur dashboard

### Gemini API Quota

- **Free Tier Limits**: 15 RPM, 1500 req/day
- **Rate Limiter Protection**: Backend enforces 20 req/hour (~0.33 RPM), well under limit
- **Monitoring**: Check Gemini API dashboard for usage

---

## Next Steps

After successful deployment:

1. **Update README.md** with live demo link
2. **Create Usage Guide** for interviewers (how to test features)
3. **Add Deployment Section** to project documentation
4. **Test All Success Criteria** (SC-001 through SC-009)
5. **Schedule Weekly Health Check** (manual or automated)

---

## Additional Resources

- **Zeabur Documentation**: https://zeabur.com/docs
- **Zeabur Status Page**: https://status.zeabur.com
- **Vite Environment Variables Guide**: https://vitejs.dev/guide/env-and-mode.html
- **FastAPI CORS Configuration**: https://fastapi.tiangolo.com/tutorial/cors/

---

**Quickstart Status**: ✅ COMPLETE  
**Last Updated**: 2025-02-17  
**Questions?** Open an issue in the CourseFlow repository.
