param(
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $root "backend"
$frontendPath = Join-Path $root "frontend"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "Python virtual environment bulunamadi: $venvPython"
}

if (-not $NoInstall) {
    Write-Host "[1/3] Backend bagimliliklari kontrol ediliyor..."
    & $venvPython -m pip install -r (Join-Path $backendPath "requirements.txt")

    Write-Host "[2/3] Frontend bagimliliklari kontrol ediliyor..."
    Push-Location $frontendPath
    npm install
    Pop-Location
}

Write-Host "[3/3] Backend ve frontend ayri pencerelerde baslatiliyor..."

$backendCmd = "Set-Location '$backendPath'; & '$venvPython' main.py"
$frontendCmd = "Set-Location '$frontendPath'; npm start"

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCmd | Out-Null
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCmd | Out-Null

Write-Host "Tamamlandi."
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"