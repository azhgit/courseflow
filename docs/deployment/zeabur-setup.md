# Zeabur Deployment Setup Guide

## Overview

This guide walks you through deploying CourseFlow (FastAPI backend + React frontend) to Zeabur Free Trial.

## Prerequisites

- Zeabur account (Free Trial with $5 credit)
- GitHub account with access to CourseFlow repository
- Gemini API key (free tier: 15 RPM, 1500 req/day)

## Step 1: Create Zeabur Project

1. Log in to [Zeabur Dashboard](https://zeabur.com)
2. Click "New Project"
3. Enter project name: `courseflow-demo`
4. Select "Free Trial" plan
5. Click "Create Project"

## Step 2: Deploy Backend Service

### 2.1 Connect Repository

1. In your project, click "Add Service"
2. Select "Git Repository"
3. Authorize Zeabur to access your GitHub account (if first time)
4. Select `CourseFlow` repository
5. Select branch: `main` (or `008-zeabur-deployment` for testing)

### 2.2 Configure Backend Service

Zeabur will automatically detect the `zeabur.json` file in the repository root and use it for backend configuration.

**Service settings:**
- Service name: `courseflow-backend`
- Root directory: `/` (repository root)
- Build command: Automatically detected from `zeabur.json`
- Start command: Automatically detected from `zeabur.json`

### 2.3 Set Environment Variables

In the Zeabur dashboard, go to your backend service settings and add the following environment variables:

**Required:**
```
GEMINI_API_KEY=<your-gemini-api-key>
```

**Optional (already set in zeabur.json):**
```
CORS_ORIGINS=https://courseflow.zeabur.app,http://localhost:5173
RATE_LIMIT_RPM=15
DATABASE_URL=sqlite+aiosqlite:///./data/courseflow.db
CHROMA_PERSIST_DIR=./data/chroma
QUOTA_HOURLY_LIMIT=20
QUOTA_DAILY_BUDGET=300
```

### 2.4 Deploy Backend

1. Click "Deploy" button
2. Wait for build to complete (~2-3 minutes)
3. Once deployed, copy the backend URL (e.g., `https://courseflow-backend-xxx.zeabur.app`)

### 2.5 Verify Backend Health

Test the health check endpoint:
```bash
curl https://courseflow-backend-xxx.zeabur.app/api/v1/health
```

Expected response:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "components": {
      "chromadb": {"status": "ok", "document_count": 42},
      "sqlite": {"status": "ok", "conversation_count": 0},
      "gemini_api": {"status": "ok"}
    },
    "uptime_seconds": 123
  }
}
```

## Step 3: Deploy Frontend Service

### 3.1 Add Frontend Service

1. In the same project, click "Add Service" again
2. Select "Git Repository"
3. Select `CourseFlow` repository
4. Select branch: `main`

### 3.2 Configure Frontend Service

**Service settings:**
- Service name: `courseflow-frontend`
- Root directory: `/src/frontend`
- Build command: Automatically detected from `src/frontend/zeabur.json`
- Output directory: `dist`
- Service type: Static Site

### 3.3 Set Frontend Environment Variables

In the Zeabur dashboard, go to your frontend service settings and add:

```
VITE_API_BASE_URL=https://courseflow-backend-xxx.zeabur.app
```

**Important:** Replace `xxx` with your actual backend service ID from Step 2.4.

### 3.4 Deploy Frontend

1. Click "Deploy" button
2. Wait for build to complete (~1-2 minutes)
3. Once deployed, copy the frontend URL (e.g., `https://courseflow-xxx.zeabur.app`)

## Step 4: Configure Auto-Deploy Webhook

Zeabur automatically configures a GitHub webhook when you link the repository.

### Verify Webhook Setup

1. Go to your GitHub repository
2. Navigate to Settings → Webhooks
3. You should see a webhook with URL containing `zeabur.com`
4. Webhook should be active with green checkmark
5. Recent deliveries should show successful responses (HTTP 200)

### Webhook Events

The webhook is configured to trigger on:
- `push` events to the `main` branch
- Pull request merges to `main`

**Auto-Deploy Flow:**
```
Git Push → GitHub Webhook → Zeabur Rebuild → New Version Live
```

Expected time: <5 minutes from push to deployment.

## Step 5: Verify End-to-End Deployment

### 5.1 Frontend Load Test

1. Open `https://courseflow-xxx.zeabur.app` in browser
2. Measure page load time (should be <3s)
3. Verify no console errors

### 5.2 Query Flow Test

1. Submit test question: "What is async/await in Python?"
2. Verify streaming response appears
3. Check browser console for errors (should be none)
4. Verify no CORS errors

### 5.3 Rate Limiting Test

Use the following script to test rate limiting:

```bash
BACKEND_URL="https://courseflow-backend-xxx.zeabur.app"

for i in {1..21}; do
  echo "Request $i:"
  curl -s -X POST "$BACKEND_URL/api/v1/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "test"}' \
    -w "\nHTTP Status: %{http_code}\n\n"
done
```

Expected behavior:
- Requests 1-20: HTTP 200 (success)
- Request 21: HTTP 429 (rate limit exceeded)

### 5.4 Auto-Redeploy Test

1. Make a minor change (e.g., update README version)
2. Commit and push to `main` branch
3. Go to Zeabur dashboard
4. Watch deployment logs
5. Verify new version is live within 5 minutes

## Step 6: Custom Domain (Optional)

If you want a custom domain instead of `*.zeabur.app`:

1. Go to frontend service settings
2. Click "Domains" tab
3. Click "Add Custom Domain"
4. Follow instructions to add DNS CNAME record
5. Wait for DNS propagation (~5-10 minutes)

## Troubleshooting

See [troubleshooting.md](./troubleshooting.md) for common issues and solutions.

## Success Criteria Checklist

After deployment, verify all success criteria:

- [ ] **SC-001**: Frontend loads in <3 seconds (use DevTools Network tab)
- [ ] **SC-002**: Health check responds in <1 second (`curl -w "%{time_total}"`)
- [ ] **SC-003**: E2E query completes in <8 seconds (submission → first token)
- [ ] **SC-004**: Rate limit active (21st request returns HTTP 429)
- [ ] **SC-005**: Auto-redeploy completes in <5 minutes (test with version bump)
- [ ] **SC-006**: Cold start handled (idle 30min, query succeeds or retries)
- [ ] **SC-007**: URLs accessible (monitor for 30 days)
- [ ] **SC-008**: No CORS errors in browser console
- [ ] **SC-009**: Rate limit persists after redeploy

## Monitoring

### View Logs

**Backend logs:**
1. Go to Zeabur dashboard
2. Select `courseflow-backend` service
3. Click "Logs" tab
4. Filter by log level or search for errors

**Frontend logs:**
1. Frontend is static, no server-side logs
2. Use browser DevTools Console for client-side errors

### Usage Monitoring

Monitor Zeabur Free Trial credit usage:
1. Go to Project settings
2. Click "Usage" tab
3. View credit consumption
4. Set up alerts if usage exceeds threshold

## Cost Estimates

**Zeabur Free Trial:**
- $5 credit (one-time)
- Backend: ~$0.10-0.20/day (estimated)
- Frontend: ~$0.05-0.10/day (estimated)
- **Total**: ~$0.15-0.30/day = **~$4.50-9.00/month**

**Note:** Free Trial $5 credit may last 16-33 days depending on actual usage.

## Next Steps

- Set up monitoring alerts
- Configure error tracking (Sentry, optional)
- Set up uptime monitoring (UptimeRobot, optional)
- Share URLs with interviewers
- Test on multiple devices/browsers
