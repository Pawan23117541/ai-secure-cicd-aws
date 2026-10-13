# Runs the pipeline's test + security checks on your own Windows PC, before you push.
# Usage (from the project root, with the venv active):
#   .\scripts\run_local_scans.ps1             -> tests + Bandit + gate
#   .\scripts\run_local_scans.ps1 -WithDocker -> also builds the image and scans it with Trivy

param([switch]$WithDocker)

New-Item -ItemType Directory -Force -Path reports | Out-Null
Remove-Item reports\bandit.json, reports\trivy.json -ErrorAction SilentlyContinue

Write-Host "`n[1/4] Lint + unit tests" -ForegroundColor Cyan
ruff check .
pytest -q

Write-Host "`n[2/4] Bandit - Python code scan" -ForegroundColor Cyan
bandit -q -r app scripts -c pyproject.toml -f json -o reports/bandit.json
bandit -q -r app scripts -c pyproject.toml

if ($WithDocker) {
    Write-Host "`n[3/4] Docker build + Trivy image scan" -ForegroundColor Cyan
    docker build -t secure-cicd-app:local .
    docker run --rm -v //var/run/docker.sock:/var/run/docker.sock -v "${PWD}/reports:/reports" `
        aquasec/trivy:0.74.0 image --severity HIGH,CRITICAL --format json `
        --output /reports/trivy.json secure-cicd-app:local
    docker run --rm -v "${PWD}/reports:/reports" aquasec/trivy:0.74.0 convert --format table /reports/trivy.json
} else {
    Write-Host "`n[3/4] Skipping Docker + Trivy (add -WithDocker to include them)" -ForegroundColor Yellow
}

Write-Host "`n[4/4] Security gate" -ForegroundColor Cyan
python scripts/security_gate.py --bandit reports/bandit.json --trivy reports/trivy.json
if ($LASTEXITCODE -eq 0) { Write-Host "GATE PASSED - safe to push" -ForegroundColor Green }
else { Write-Host "GATE FAILED - fix the findings above before pushing" -ForegroundColor Red }
