# Force reset Python environment to base (not kth)
# Run this script to clear VS Code cache and force base environment

param(
    [switch]$Force
)

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$vscodeStoragePath = "C:\Users\12434\AppData\Roaming\Code\User\workspaceStorage\ca4e7f0fc4d6b7b2135070e2312de395"

Write-Host "========================================" -ForegroundColor Green
Write-Host "Resetting Python environment to BASE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Step 1: Kill VS Code
Write-Host "[1/3] Closing VS Code instances..." -ForegroundColor Cyan
$vscodeProcesses = Get-Process code -ErrorAction SilentlyContinue
if ($vscodeProcesses) {
    Stop-Process -Name code -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "  ✓ VS Code closed" -ForegroundColor Green
} else {
    Write-Host "  ✓ VS Code not running" -ForegroundColor Green
}

# Step 2: Clear cache
Write-Host "[2/3] Clearing VS Code cache..." -ForegroundColor Cyan
if (Test-Path $vscodeStoragePath) {
    try {
        Remove-Item -Path "$vscodeStoragePath\*" -Recurse -Force -ErrorAction Stop
        Write-Host "  ✓ Cache cleared" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ Could not fully clear cache (some files in use)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✓ Cache already clean" -ForegroundColor Green
}

# Step 3: Set environment variables
Write-Host "[3/3] Setting environment variables..." -ForegroundColor Cyan
[System.Environment]::SetEnvironmentVariable('CONDA_DEFAULT_ENV', 'base', 'User')
[System.Environment]::SetEnvironmentVariable('CONDA_PREFIX', 'D:\Anaconda', 'User')
Write-Host "  ✓ Environment variables set" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ Done! Reopen VS Code now" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Close all VS Code windows"
Write-Host "2. Reopen VS Code"
Write-Host "3. You should now see 'base (3.11.7)' in bottom-right corner"
Write-Host ""
