# Urban Pulse AI — One-Click Startup Script
# Starts the API server and opens the dashboard

Write-Host ""
Write-Host "  =====================================================" -ForegroundColor Cyan
Write-Host "  URBAN PULSE AI — Startup" -ForegroundColor Cyan
Write-Host "  =====================================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
$venvPath = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "  [OK] Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "  [!] No .venv found. Run: python -m venv .venv" -ForegroundColor Red
    exit 1
}

# Check if model exists
$modelPath = ".\models\congestion_model.joblib"
if (-not (Test-Path $modelPath)) {
    Write-Host "  [!] Model not found. Training now..." -ForegroundColor Yellow
    python backend/train_model.py
    Write-Host ""
}

# Start API server in background
Write-Host "  [1] Starting API server..." -ForegroundColor Yellow
$apiJob = Start-Process -FilePath "python" -ArgumentList "backend/api.py" -PassThru -NoNewWindow
Start-Sleep -Seconds 2

# Check if API is running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 3
    Write-Host "  [OK] API server running at http://localhost:8000" -ForegroundColor Green
} catch {
    Write-Host "  [!] API server failed to start" -ForegroundColor Red
    exit 1
}

# Open dashboard in browser
Write-Host "  [2] Opening dashboard..." -ForegroundColor Yellow
Start-Process "http://localhost:8000"
Write-Host "  [OK] Dashboard opened in browser" -ForegroundColor Green

Write-Host ""
Write-Host "  =====================================================" -ForegroundColor Cyan
Write-Host "  READY! Dashboard: http://localhost:8000" -ForegroundColor Green
Write-Host "  =====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  To run video analytics (separate terminal):" -ForegroundColor White
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "    python backend/analytics.py --source 0" -ForegroundColor Gray
Write-Host ""
Write-Host "  Press Ctrl+C to stop the server" -ForegroundColor DarkGray
Write-Host ""

# Wait for API process
try {
    $apiJob | Wait-Process
} catch {
    Write-Host "`n  [INFO] Shutting down..." -ForegroundColor Yellow
    Stop-Process -Id $apiJob.Id -Force -ErrorAction SilentlyContinue
}
