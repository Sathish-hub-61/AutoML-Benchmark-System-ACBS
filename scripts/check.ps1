$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== 1/3 Running Ruff Lint ===" -ForegroundColor Cyan
python -m ruff check src tests app scripts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== 2/3 Running Pytest Suite ===" -ForegroundColor Cyan
python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== 3/3 Running FakeAdapter Smoke Test ===" -ForegroundColor Cyan
python scripts/smoke_fake_adapter.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== All Checks Passed! ===" -ForegroundColor Green

