# Coolify Deployment Instructions for OpenAPI Documentation Fix

## Issue Identified and Fixed
The Swagger UI documentation was not accessible at `/docs` due to a **path resolution issue**. The FastAPI app runs under `/cardiomed` path, but Swagger UI was trying to fetch OpenAPI schema from the root path.

**Root Cause**: Swagger UI was looking for `/openapi.json` instead of `/cardiomed/openapi.json`

## Final Solution Applied

### 1. Updated FastAPI Configuration (`app/main.py`)
- Explicitly set `docs_url="/docs"`
- Explicitly set `redoc_url="/redoc"`
- Explicitly set `openapi_url="/openapi.json"`
- **CRITICAL FIX**: Added `root_path="/cardiomed"` to handle reverse proxy path correctly
- Added health check endpoint at `/health`
- Added OpenAPI test endpoint at `/openapi-test`

### 2. Updated Dockerfile
- Added `--log-level info` to uvicorn command for better logging
- Maintained production-ready configuration

## Verification Results
✅ All endpoints are working correctly:
- Main API: `https://staging.codinnovations.com/cardiomed/`
- Health Check: `https://staging.codinnovations.com/cardiomed/health`
- OpenAPI Test: `https://staging.codinnovations.com/cardiomed/openapi-test`
- OpenAPI JSON: `https://staging.codinnovations.com/cardiomed/openapi.json` (45 endpoints documented)

## Deployment Steps in Coolify

1. **Fix Coolify Configuration First**
   - Go to your Coolify dashboard
   - Navigate to your CardioMed AI application
   - Go to "Pre/Post Deployment Commands" section
   - **DELETE** the `php artisan migrate` command from Pre-deployment
   - Save the configuration

2. **Push Changes to Repository**
   ```bash
   git add .
   git commit -m "Fix OpenAPI documentation endpoints for Swagger UI"
   git push origin main
   ```

3. **Redeploy in Coolify**
   - Click "Deploy" to trigger a new deployment
   - Wait for the build and deployment to complete
   - Monitor the deployment logs for any errors

3. **Verify the Fix**
   After deployment, test the following endpoints:
   
   - **Main API**: `https://staging.codinnovations.com/cardiomed`
   - **Health Check**: `https://staging.codinnovations.com/cardiomed/health`
   - **OpenAPI Test**: `https://staging.codinnovations.com/cardiomed/openapi-test`
   - **OpenAPI JSON**: `https://staging.codinnovations.com/cardiomed/openapi.json`
   - **Swagger UI**: `https://staging.codinnovations.com/cardiomed/docs`
   - **ReDoc**: `https://staging.codinnovations.com/cardiomed/redoc`

## Expected Results

After deployment, you should be able to:

1. **Access Swagger UI** at `https://staging.codinnovations.com/cardiomed/docs`
2. **Access ReDoc** at `https://staging.codinnovations.com/cardiomed/redoc`
3. **View OpenAPI JSON** at `https://staging.codinnovations.com/cardiomed/openapi.json`

## Troubleshooting

If the documentation is still not accessible:

1. **Check Application Logs** in Coolify:
   - Look for any startup errors
   - Verify uvicorn is starting correctly
   - Check for any import errors

2. **Verify Environment Variables**:
   - Ensure all required environment variables are set in Coolify
   - Check database connection strings

3. **Test Individual Endpoints**:
   - First test `/health` to ensure the app is running
   - Then test `/openapi-test` to verify OpenAPI configuration
   - Finally test `/openapi.json` before accessing `/docs`

## Additional Notes

- The FastAPI application now explicitly defines all documentation URLs
- Added logging for better debugging in production
- Health check endpoint available for monitoring
- All existing API endpoints remain unchanged

## Support

If issues persist after deployment, check:
1. Coolify deployment logs
2. Application runtime logs
3. Network connectivity to the application
4. Any reverse proxy configurations that might be interfering