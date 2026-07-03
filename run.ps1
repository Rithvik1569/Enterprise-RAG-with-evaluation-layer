Write-Host "Starting Antigravity RAG SaaS System..." -ForegroundColor Cyan

# Check if port 8000 is occupied
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "Warning: Port 8000 (Backend) is already in use." -ForegroundColor Yellow
} else {
    Write-Host "Launching Backend on Port 8000 in a new window..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
}

# Check if port 5173 is occupied
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port5173) {
    Write-Host "Warning: Port 5173 (Frontend) is already in use." -ForegroundColor Yellow
} else {
    Write-Host "Launching Frontend on Port 5173 in a new window..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
}

Write-Host "Done! The frontend should be accessible at http://localhost:5173" -ForegroundColor Cyan
