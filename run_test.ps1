# PowerShell script to run tests
# Starts backend and runs isolation tests

Write-Host "Starting backend server..." -ForegroundColor Green
$backend = Start-Process python -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" -PassThru -WindowStyle Hidden

Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "Running isolation tests..." -ForegroundColor Green
python test_user_isolation.py

Write-Host "Stopping backend..." -ForegroundColor Yellow
Stop-Process -Id $backend.Id -Force

Write-Host "Test completed!" -ForegroundColor Green

