# One-shot local setup for Windows PowerShell: env file, Ollama models, containers, migrations, seed data.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example (edit JWT_SECRET_KEY before sharing this machine)."
}

$envLines = Get-Content .env
$model = (($envLines | Where-Object { $_ -match '^OLLAMA_MODEL=' }) -replace '^OLLAMA_MODEL=', '')
$embedModel = (($envLines | Where-Object { $_ -match '^EMBEDDING_MODEL=' }) -replace '^EMBEDDING_MODEL=', '')
if (-not $model) { $model = "qwen2.5:7b" }
if (-not $embedModel) { $embedModel = "nomic-embed-text" }

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "Pulling Ollama models: $model and $embedModel"
    ollama pull $model
    ollama pull $embedModel
} else {
    Write-Warning "ollama not found. Install it from https://ollama.com, then run: ollama pull $model; ollama pull $embedModel"
}

docker compose up -d --build
Write-Host "Waiting for the backend to become healthy..."
do {
    Start-Sleep -Seconds 2
    try { $ok = (Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/health).StatusCode -eq 200 } catch { $ok = $false }
} until ($ok)

docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed

Write-Host ""
Write-Host "Ready! Frontend: http://localhost:5173  API docs: http://localhost:8000/docs"
