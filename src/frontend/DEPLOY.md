# CourseFlow React Chat Frontend - Deployment Guide

## Overview
The CourseFlow React Chat frontend is a Vite-based single-page application (SPA) that connects to the CourseFlow RAG backend API. This guide covers building, testing, and deploying to Zeabur.

## Prerequisites
- Node.js 18+ installed
- npm or yarn package manager
- CourseFlow backend deployed and accessible at `https://courseflow-backend.zeabur.app`
- Zeabur account with project access

## Environment Configuration

### Development (`.env`)
```bash
VITE_API_BASE_URL=http://localhost:8000
```
Uses local backend on port 8000.

### Production (`.env.production`)
```bash
VITE_API_BASE_URL=https://courseflow-backend.zeabur.app
```
Points to Zeabur-deployed backend. Update this URL if your backend deployment location changes.

## Building for Production

### 1. Install Dependencies
```bash
cd src/frontend
npm install
```

### 2. Build the Application
```bash
npm run build
```

**Output:**
- `dist/index.html` - Entry point
- `dist/assets/index-*.js` - JavaScript bundle (code-split)
- `dist/assets/index-*.css` - Tailwind CSS bundle
- Typical bundle size: ~64 kB gzipped

**Verification:**
```bash
# Should see "dist/" directory with all assets
ls -la dist/

# Check gzip sizes
gzip -c dist/assets/index-*.js | wc -c
gzip -c dist/assets/index-*.css | wc -c
```

### 3. Test Production Build Locally
```bash
npm run preview
```
Opens a local preview at `http://localhost:4173` with production assets. Use this to verify:
- No console errors
- No broken imports
- API communication works (requires backend running)
- Page loads correctly
- Chat input/output functional

## Deployment to Zeabur

### Option 1: Git-based Deployment (Recommended)

Zeabur supports automatic deployment from GitHub via webhook:

1. **Push to GitHub**
   ```bash
   git push origin 007-react-frontend-mvp
   ```

2. **Configure Zeabur Project**
   - Log in to Zeabur dashboard
   - Create new project or select existing `courseflow` project
   - Select "Deploy from GitHub"
   - Choose repository: `<username>/courseflow`
   - Select branch: `007-react-frontend-mvp`
   - Set root directory: `src/frontend`

3. **Configure Build Settings**
   - Framework: Vite
   - Build command: `npm run build`
   - Output directory: `dist`
   - Start command: Not needed (static SPA)
   - Environment variables:
     ```
     VITE_API_BASE_URL=https://courseflow-backend.zeabur.app
     ```

4. **Deploy**
   - Zeabur automatically builds and deploys on push
   - Monitor deployment status in dashboard
   - After ~2 minutes, access app at assigned domain (e.g., `https://courseflow-frontend.zeabur.app`)

### Option 2: Manual Deployment via Zeabur CLI

If you prefer direct deployment:

```bash
# Install Zeabur CLI (if not already installed)
npm install -g zeabur

# Authenticate with Zeabur
zeabur auth login

# Deploy from src/frontend directory
zeabur deploy --root src/frontend
```

## Validation Checklist

Before marking deployment complete, verify all success criteria:

### SC-001: First Word <1.5s
- [ ] Submit a question
- [ ] Measure time from Submit to first word appears
- [ ] Should be <1500ms (typical: 800-1200ms with network latency)

### SC-002: Smooth Streaming
- [ ] Watch Chrome DevTools Network tab during response
- [ ] Chunks should arrive every 50-200ms
- [ ] No 1+ second gaps between chunks
- [ ] Text appears smoothly, not in large batches

### SC-003: Sources Below Answer
- [ ] Submit question expecting documents in knowledge base
- [ ] Wait for response to complete (not in-progress)
- [ ] Verify source documents listed below message
- [ ] Format: `📄 document-name.md`

### SC-004: New Chat Resets Everything
- [ ] Chat with assistant, build multi-message conversation
- [ ] Click "New Chat" button
- [ ] Confirm dialog appears
- [ ] After confirmation: empty chat, input cleared, no messages visible

### SC-005: Error Messages Match Spec
Test each error scenario:

**Rate Limit (429 - hourly)**
- Expected: "Demo limit reached. Try again in 1 hour."

**Quota Exhausted (429 - daily)**
- Expected: "Daily demo limit reached. Resets at midnight."

**No Relevant Documents**
- Expected: "No content found for this query. Try rephrasing your question."

**Network Failure**
- Expected: "Connection lost. Please check your network and try again."
- Verify Retry button appears and works

### SC-006: Responsive Design
- [ ] Resize browser to 375px width (mobile)
  - Input field visible and usable
  - Message bubbles wrap correctly
  - No horizontal overflow
  - Touch targets at least 44x44px
  
- [ ] Resize to 1280px width (desktop)
  - Full width utilization
  - Message bubbles max-width reasonable (~600px)
  - Sidebar/layout doesn't break

### SC-007: End-to-End <60s
- [ ] Start stopwatch on page load
- [ ] Submit question
- [ ] Wait for complete response with sources
- [ ] Stop stopwatch when answer finishes
- [ ] Should be <60 seconds (typical: 15-30 seconds)

### SC-008: Session Persistence
- [ ] Load app, submit 2-3 questions, build conversation
- [ ] Refresh page (F5)
- [ ] All messages should still be visible
- [ ] Conversation ID should remain the same
- [ ] Can continue conversation with follow-up

### SC-009: Example Cache Hits
- [ ] Click on an example question
- [ ] Measure response time (should be very fast, <500ms)
- [ ] Response should be consistent (cached)

## Monitoring & Troubleshooting

### Common Issues

**CORS Errors**
- Symptom: Browser console shows "CORS policy blocked request"
- Cause: Backend not accessible from frontend domain
- Solution: Verify `VITE_API_BASE_URL` correct in `.env.production` and backend CORS headers configured

**Blank Page / 404**
- Symptom: Browser loads but shows blank page
- Cause: HTML not served correctly
- Solution: 
  - Check Zeabur build output logs
  - Verify `dist/index.html` exists after build
  - Check if build command ran successfully

**API Timeout**
- Symptom: Chat submit works but no response comes back
- Cause: Backend slow or unreachable
- Solution:
  - Test backend health: `curl https://courseflow-backend.zeabur.app/health`
  - Check backend deployment status in Zeabur
  - Verify network connectivity from frontend domain

**Build Failures**
- Symptom: Zeabur build reports errors
- Solution:
  - Check Zeabur build logs
  - Verify all dependencies in `package.json`
  - Ensure `npm run build` works locally first
  - Check for environment variable issues

### Performance Monitoring

After deployment, monitor performance:

1. **Lighthouse Audit** (Chrome DevTools)
   - Target: Performance >90, Accessibility >95
   - Report: Check Core Web Vitals (LCP, FID, CLS)

2. **Network Waterfall**
   - Verify JavaScript bundle loads <2s
   - Verify CSS loads <1s
   - API calls should start <300ms after page load

3. **Chrome DevTools Performance Tab**
   - Record page load
   - Check main thread activity
   - Look for long tasks blocking interaction

## Rollback Procedure

If deployment has issues:

1. **Via Zeabur Dashboard**
   - Go to Deployment History
   - Select previous working version
   - Click "Redeploy"

2. **Via Git**
   - Revert commit: `git revert <commit-hash>`
   - Push: `git push origin 007-react-frontend-mvp`
   - Zeabur automatically redeploys

## Next Steps

After successful deployment:

1. Share public URL with team/interviewers
2. Test across browsers (Chrome, Firefox, Safari, mobile browsers)
3. Monitor error logs and performance metrics
4. Gather feedback and iterate
5. Consider Phase 6 (Styling enhancements) for polish if needed

## Support

For deployment issues:
- Check Zeabur logs: Dashboard → Project → Deployment → Logs
- Verify backend is running: Check `https://courseflow-backend.zeabur.app/health`
- Test frontend locally: `npm run preview` and check for errors
- Review `.env.production` for correct API URL
