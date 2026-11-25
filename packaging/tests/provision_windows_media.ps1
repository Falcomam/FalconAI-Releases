# Place digest-verified FFmpeg tools on PATH for this runner's test steps.
$ErrorActionPreference = 'Stop'
$archive = Join-Path $env:RUNNER_TEMP 'ffmpeg-8.0.1-essentials.zip'
$folder = Join-Path $env:RUNNER_TEMP 'falcon-media-tools'
$url = 'https://github.com/GyanD/codexffmpeg/releases/download/8.0.1/ffmpeg-8.0.1-essentials_build.zip'
$sha256 = 'e2aaeaa0fdbc397d4794828086424d4aaa2102cef1fb6874f6ffd29c0b88b673'
Invoke-WebRequest -Uri $url -OutFile $archive -MaximumRetryCount 3
if ((Get-FileHash $archive -Algorithm SHA256).Hash -ne $sha256) { throw 'FFmpeg download digest mismatch' }
Expand-Archive -LiteralPath $archive -DestinationPath $folder -Force
$bin = Join-Path $folder 'ffmpeg-8.0.1-essentials_build\bin'
foreach ($name in 'ffmpeg.exe','ffprobe.exe') {
    $program = Join-Path $bin $name
    & $program -version
    if ($LASTEXITCODE -ne 0) { throw "$name failed its version check" }
}
$bin | Out-File -FilePath $env:GITHUB_PATH -Encoding utf8 -Append
