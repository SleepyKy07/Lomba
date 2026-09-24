# Serve frontend static Tahap 1 (tanpa web.py / Python app server).
# Usage: pwsh -File scripts/serve-frontend.ps1  [port]
param([int]$Port = 8080)
$root = Join-Path $PSScriptRoot "..\docs"
Write-Host "Serve $root -> http://localhost:$Port"
Write-Host "Frontend only. Data via Supabase (isi docs/js/config.js)."
python -m http.server $Port --bind 127.0.0.1 --directory $root
