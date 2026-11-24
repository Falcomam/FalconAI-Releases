param(
  [Parameter(Mandatory=$true)][int]$WaitPid,
  [Parameter(Mandatory=$true)][string]$Installer,
  [Parameter(Mandatory=$true)][string]$AppExe
)
$ErrorActionPreference = 'Stop'
$falconData = Join-Path $env:LOCALAPPDATA 'FalconAI'
$logDir = Join-Path $falconData 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir 'app_installer_update.log'
function Log([string]$Message) {
  Add-Content -LiteralPath $logFile -Value ("$(Get-Date -Format o) " + $Message) -Encoding UTF8
}
try {
  $Installer = [System.IO.Path]::GetFullPath($Installer)
  $AppExe = [System.IO.Path]::GetFullPath($AppExe)
  $appDir = Split-Path -Parent $AppExe
  $safeCache = Join-Path $falconData 'installer_updates'
  if (-not $Installer.StartsWith(($safeCache.TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase) -or
      (Split-Path -Leaf $Installer) -ne 'Falcon_Ai_Setup.exe' -or
      -not (Test-Path -LiteralPath $Installer -PathType Leaf) -or
      -not (Test-Path -LiteralPath $AppExe -PathType Leaf) -or
      (Split-Path -Leaf $AppExe) -ne 'Falcon Ai.exe') {
    throw 'Unsafe or missing Falcon Ai installer/application path'
  }
  Log ('Installer handoff started. Previous PID ' + $WaitPid)
  $stillRunning = $false
  for ($i=0; $i -lt 120; $i++) {
    $process = Get-Process -Id $WaitPid -ErrorAction SilentlyContinue
    if (-not $process) { break }
    $stillRunning = $true
    Start-Sleep -Milliseconds 500
  }
  if (Get-Process -Id $WaitPid -ErrorAction SilentlyContinue) {
    throw 'Falcon Ai did not exit. Installation stopped; old version untouched'
  }
  Log 'Original GUI closed. Installing verified new Falcon Ai release'
  $argString = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR="' + $appDir + '"'
  $proc = Start-Process -FilePath $Installer -ArgumentList $argString -PassThru -Wait
  Log ('Installer exit code ' + $proc.ExitCode)
  if ($proc.ExitCode -ne 0) {
    throw ('Installer returned non-zero exit code ' + $proc.ExitCode)
  }
  if (-not (Test-Path -LiteralPath $AppExe -PathType Leaf)) {
    throw 'Installer returned success but new Falcon Ai executable is missing'
  }
  # Relaunch new executable, never a stale batch file or old Python folder.
  $newProcess = Start-Process -FilePath $AppExe -WorkingDirectory $appDir -PassThru
  Log ('Launched installed Falcon Ai executable, PID ' + $newProcess.Id)
  Start-Sleep -Seconds 4
  $newProcess.Refresh()
  if ($newProcess.HasExited) {
    Log ('WARNING: Newly installed application exited early with code ' + $newProcess.ExitCode)
  } else {
    Log 'New Falcon Ai application is running'
  }
} catch {
  Log ('UPDATE ERROR: ' + $_.Exception.Message)
  exit 1
}
