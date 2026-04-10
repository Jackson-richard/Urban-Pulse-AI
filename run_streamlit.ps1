# Cleanup any existing API process running on port 8000
$existingApi = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existingApi) {
    Write-Host "Stopping existing API server on port 8000..." -ForegroundColor Yellow
    Stop-Process -Id $existingApi.OwningProcess -Force -ErrorAction SilentlyContinue
}

# Start the API Backend
Write-Host "Starting API Backend..." -ForegroundColor Green
Start-Process "powershell" -ArgumentList "-NoExit -Command `"cd 'c:\Users\Jackson\OneDrive\Documents\urban pulse AI'; .\.venv\Scripts\Activate.ps1; python backend/api.py`""
Start-Sleep -Seconds 3

# Start the Analytics processing 
Write-Host "Starting Real-time OpenCV Analytics Engine..." -ForegroundColor Green
Start-Process "powershell" -ArgumentList "-NoExit -Command `"cd 'c:\Users\Jackson\OneDrive\Documents\urban pulse AI'; .\.venv\Scripts\Activate.ps1; python backend/analytics.py --source data/video.mp4`""
Start-Sleep -Seconds 3

# Start the new Streamlit Dashboard
Write-Host "Launching Streamlit Dashboard..." -ForegroundColor Green
Start-Process "powershell" -ArgumentList "-NoExit -Command `"cd 'c:\Users\Jackson\OneDrive\Documents\urban pulse AI'; .\.venv\Scripts\Activate.ps1; streamlit run dashboard.py`""

Write-Host "All systems successfully launched! Streamlit is opening in your web browser." -ForegroundColor Cyan
