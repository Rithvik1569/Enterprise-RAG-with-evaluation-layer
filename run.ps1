Write-Host "Starting Enterprise RAG SaaS System Globally..." -ForegroundColor Cyan

# The backend now requires MongoDB. Since Docker is not installed, it will use the MONGODB_URL in backend/.env
Write-Host "NOTE: Make sure your MongoDB Atlas URL is set in backend/.env!" -ForegroundColor Yellow

# Check if port 8000 is occupied and kill it
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "Closing existing process on Port 8000 (Backend)..." -ForegroundColor Yellow
    $port8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}
Write-Host "Launching Backend on Port 8000 in a new window..." -ForegroundColor Green
$BackendDir = Resolve-Path ".\backend"
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$($BackendDir.Path)'; & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir ."

Write-Host "Waiting for Backend to become ready..." -ForegroundColor Yellow
$retryCount = 0
while ($retryCount -lt 40) {
    $tcp = [System.Net.Sockets.TcpClient]::new()
    try {
        $tcp.Connect("127.0.0.1", 8000)
        $tcp.Close()
        Write-Host "Backend is online!" -ForegroundColor Green
        break
    } catch {
        Start-Sleep -Milliseconds 500
        $retryCount++
    }
}

# Check if port 5173 is occupied and kill it
$port5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($port5173) {
    Write-Host "Closing existing process on Port 5173 (Frontend)..." -ForegroundColor Yellow
    $port5173 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}
Write-Host "Launching Frontend on Port 5173 in a new window..." -ForegroundColor Green
$FrontendDir = Resolve-Path ".\frontend"
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$($FrontendDir.Path)'; npm run dev"

# Fetch the local IP addresses to give the user the global network links
$ipAddresses = (Get-NetIPAddress -AddressFamily IPv4 -Type Unicast | Where-Object { $_.IPAddress -ne "127.0.0.1" }).IPAddress

Write-Host "Done! The application is running globally on your network." -ForegroundColor Cyan
Write-Host "You can access the frontend from any device on your Wi-Fi at:" -ForegroundColor White
foreach ($ip in $ipAddresses) {
    Write-Host "👉 http://${ip}:5173" -ForegroundColor Green
}
if ($ipAddresses.Count -gt 0) {
    Write-Host "(Your backend API docs are hosted at http://$($ipAddresses[0]):8000/docs)" -ForegroundColor Gray
}
