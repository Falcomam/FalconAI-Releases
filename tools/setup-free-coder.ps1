# Falcon AI — opt-in free local coding model setup
# Run by choice in PowerShell. No API keys, subscription, or paid services.
# Does not run generated code or modify Windows drivers/Power settings.
$ErrorActionPreference = "Stop"
$model = "qwen2.5-coder:7b"
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Error "Ollama was not found. Install Ollama from https://ollama.com/download/windows first, then run this script again."
    exit 1
}
Write-Host "Falcon AI - free local coding model" -ForegroundColor Magenta
Write-Host "Model: $model"
Write-Host "Downloading model weights from Ollama. This may consume several GB of disk space and network data."
Write-Host "No cloud AI API will be configured. Falcon retains its existing approvals and STOP controls."
$answer = Read-Host "Download/install this free model? Type YES to proceed"
if ($answer -cne "YES") {
    Write-Host "Canceled. No model was downloaded by this script."
    exit 0
}
& $ollama.Source pull $model
if ($LASTEXITCODE -ne 0) {
    Write-Error "Model download failed (Ollama exit code $LASTEXITCODE). Falcon settings were not changed."
    exit 1
}
$models = & $ollama.Source list
if ($LASTEXITCODE -ne 0 -or -not ($models | Select-String -SimpleMatch $model)) {
    Write-Error "Ollama did not confirm the requested model. Falcon settings were not changed."
    exit 1
}
Write-Host "The model is installed." -ForegroundColor Green
Write-Host "Next: open Falcon AI 14, enter /engine list, then /engine use-code $model"
Write-Host "Keep your current chat model for conversation; use the coding model for projects."
