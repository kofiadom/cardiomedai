#!/usr/bin/env python3
"""
Validation script to check FastAPI OpenAPI configuration
This script validates the syntax and configuration without running the server
"""

import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def validate_fastapi_config():
    """Validate the FastAPI configuration for OpenAPI documentation"""
    
    print("Validating FastAPI OpenAPI configuration...")
    
    # Check if the main.py file exists and has correct structure
    main_py_path = os.path.join('app', 'main.py')
    if not os.path.exists(main_py_path):
        print("ERROR: app/main.py not found")
        return False
    
    # Read and validate the main.py content
    with open(main_py_path, 'r') as f:
        content = f.read()
    
    # Check for required FastAPI configuration
    required_configs = [
        'docs_url="/docs"',
        'redoc_url="/redoc"', 
        'openapi_url="/openapi.json"',
        'title="CardioMed AI API"'
    ]
    
    missing_configs = []
    for config in required_configs:
        if config not in content:
            missing_configs.append(config)
    
    if missing_configs:
        print("ERROR: Missing required FastAPI configurations:")
        for config in missing_configs:
            print(f"   - {config}")
        return False
    
    # Check for health endpoints
    health_endpoints = [
        '@app.get("/health")',
        '@app.get("/openapi-test")'
    ]
    
    for endpoint in health_endpoints:
        if endpoint not in content:
            print(f"WARNING: Optional endpoint missing: {endpoint}")
    
    print("SUCCESS: FastAPI OpenAPI configuration is valid!")
    print("\nExpected endpoints after deployment:")
    print("   - Main API: https://staging.codinnovations.com/cardiomed")
    print("   - Health Check: https://staging.codinnovations.com/cardiomed/health")
    print("   - OpenAPI JSON: https://staging.codinnovations.com/cardiomed/openapi.json")
    print("   - Swagger UI: https://staging.codinnovations.com/cardiomed/docs")
    print("   - ReDoc: https://staging.codinnovations.com/cardiomed/redoc")
    
    return True

def validate_dockerfile():
    """Validate Dockerfile configuration"""
    
    print("\nValidating Dockerfile configuration...")
    
    if not os.path.exists('Dockerfile'):
        print("ERROR: Dockerfile not found")
        return False
    
    with open('Dockerfile', 'r') as f:
        content = f.read()
    
    # Check for uvicorn command
    if 'uvicorn app.main:app' not in content:
        print("ERROR: uvicorn command not found in Dockerfile")
        return False
    
    if '--host 0.0.0.0 --port 8000' not in content:
        print("ERROR: Correct host and port configuration not found")
        return False
    
    print("SUCCESS: Dockerfile configuration is valid!")
    return True

if __name__ == "__main__":
    print("CardioMed AI - OpenAPI Configuration Validator")
    print("=" * 50)
    
    fastapi_valid = validate_fastapi_config()
    dockerfile_valid = validate_dockerfile()
    
    if fastapi_valid and dockerfile_valid:
        print("\nAll configurations are valid!")
        print("\nNext steps:")
        print("1. Commit and push changes to your repository")
        print("2. Redeploy in Coolify")
        print("3. Test the /docs endpoint")
        sys.exit(0)
    else:
        print("\nConfiguration validation failed!")
        sys.exit(1)