Write-Host "Checking port 8000..." -ForegroundColor Cyan

$connections = netstat -ano | Select-String ":8000"

if ($connections) {
    Write-Host "Something is using/reserving port 8000:" -ForegroundColor Yellow
    $connections

    $pids = $connections.ToString() |
        ForEach-Object {
            ($_ -split '\s+')[-1]
        } |
        Where-Object { $_ -match '^\d+$' } |
        Select-Object -Unique

    foreach ($pid in $pids) {
        if ($pid -ne "0") {
            Write-Host "PID: $pid" -ForegroundColor Yellow
            tasklist /FI "PID eq $pid"
        }
    }
} else {
    Write-Host "Port 8000 is free." -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting HackGrid backend..." -ForegroundColor Cyan

Set-Location "C:\Users\Shashank Kotnala\OneDrive\Documents\HackGrid_new"

python -m uvicorn Backend.server:app --host 127.0.0.1 --port 8000 --reload