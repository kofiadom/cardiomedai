# Swagger UI Troubleshooting Guide

## Current Status
✅ **OpenAPI JSON endpoint is working** - The `/openapi.json` endpoint returns valid OpenAPI schema
❌ **Swagger UI fails to load** - Getting 404 error when Swagger UI tries to fetch `/openapi.json`

## Root Cause Analysis

### Issue Identified: Coolify Configuration Problems

1. **Incorrect Pre-deployment Command**
   - Current: `php artisan migrate` 
   - Problem: This is a PHP/Laravel command, not Python/FastAPI
   - Impact: May cause deployment failures or unexpected behavior

2. **Potential Caching/Deployment Issue**
   - The OpenAPI JSON is actually being served correctly
   - Swagger UI might be cached or not updated after deployment

## Immediate Fix Steps

### Step 1: Fix Coolify Configuration
1. Go to Coolify Dashboard
2. Navigate to your CardioMed AI application
3. Go to "Pre/Post Deployment Commands"
4. **DELETE** the `php artisan migrate` command from Pre-deployment
5. Save configuration

### Step 2: Force Fresh Deployment
1. Push any small change to trigger rebuild:
   ```bash
   git add .
   git commit -m "Force rebuild for Swagger UI fix"
   git push origin main
   ```
2. In Coolify, click "Deploy" 
3. Monitor deployment logs

### Step 3: Clear Browser Cache
1. Hard refresh the docs page: `Ctrl+F5` or `Cmd+Shift+R`
2. Or open in incognito/private mode
3. Try: `https://staging.codinnovations.com/cardiomed/docs`

## Verification Steps

Test these endpoints in order:

1. **Main API**: `https://staging.codinnovations.com/cardiomed`
   - Should return JSON with endpoints list

2. **Health Check**: `https://staging.codinnovations.com/cardiomed/health`
   - Should return: `{"status": "healthy", "message": "CardioMed AI API is running"}`

3. **OpenAPI Test**: `https://staging.codinnovations.com/cardiomed/openapi-test`
   - Should return OpenAPI endpoint information

4. **OpenAPI JSON**: `https://staging.codinnovations.com/cardiomed/openapi.json`
   - Should return full OpenAPI schema JSON

5. **Swagger UI**: `https://staging.codinnovations.com/cardiomed/docs`
   - Should load interactive documentation

## Alternative Solutions

### If Swagger UI Still Doesn't Work:

1. **Try ReDoc instead**: `https://staging.codinnovations.com/cardiomed/redoc`
   - ReDoc is more reliable than Swagger UI in some environments

2. **Manual OpenAPI Schema Access**:
   - Download the JSON from `/openapi.json`
   - Use external Swagger UI: https://editor.swagger.io/
   - Paste the JSON schema there

3. **Check Coolify Logs**:
   - Look for any startup errors
   - Check if uvicorn is starting correctly
   - Verify no import errors

## Technical Details

### FastAPI Configuration (Already Fixed)
```python
app = FastAPI(
    title="CardioMed AI API",
    description="An API for managing blood pressure readings and health monitoring",
    version="0.1.0",
    docs_url="/docs",           # Swagger UI
    redoc_url="/redoc",         # ReDoc
    openapi_url="/openapi.json" # OpenAPI schema
)
```

### Expected Behavior
- FastAPI automatically generates OpenAPI schema
- Swagger UI fetches schema from `/openapi.json`
- All endpoints should be documented automatically

## Contact Support

If issues persist after following these steps:
1. Check Coolify deployment logs
2. Verify all environment variables are set
3. Test individual API endpoints to ensure app is running
4. Consider using ReDoc as alternative documentation interface