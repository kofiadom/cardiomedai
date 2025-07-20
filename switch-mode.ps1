# PowerShell script to switch between local and Docker development modes

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("local", "docker")]
    [string]$Mode
)

Write-Host "Switching to $Mode mode..." -ForegroundColor Green

if ($Mode -eq "local") {
    # Switch to local development mode
    Write-Host "Setting TOOLBOX_URL to localhost:5000" -ForegroundColor Yellow
    
    # Update .env file for local development
    $envContent = Get-Content .env
    $envContent = $envContent -replace 'TOOLBOX_URL="http://toolbox:5000"', 'TOOLBOX_URL="http://localhost:5000"'
    $envContent | Set-Content .env
    
    Write-Host "✅ Configured for local development" -ForegroundColor Green
    Write-Host "To run locally:" -ForegroundColor Cyan
    Write-Host "1. Start MCP Toolbox: docker run --rm -p 5000:5000 -v `"./app/advisor_agent/tools.yaml:/tools.yaml`" us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:0.7.0 /toolbox --tools-file /tools.yaml --address 0.0.0.0 --port 5000" -ForegroundColor White
    Write-Host "2. Start FastAPI: uv run app/main.py" -ForegroundColor White
}
elseif ($Mode -eq "docker") {
    # Switch to Docker mode
    Write-Host "Setting TOOLBOX_URL to toolbox:5000" -ForegroundColor Yellow
    
    # Update .env file for Docker
    $envContent = Get-Content .env
    $envContent = $envContent -replace 'TOOLBOX_URL="http://localhost:5000"', 'TOOLBOX_URL="http://toolbox:5000"'
    $envContent | Set-Content .env
    
    Write-Host "✅ Configured for Docker deployment" -ForegroundColor Green
    Write-Host "To run with Docker:" -ForegroundColor Cyan
    Write-Host "docker-compose up --build" -ForegroundColor White
}

Write-Host "Mode switch complete!" -ForegroundColor Green
