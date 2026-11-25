# Run on an isolated Windows CI runner after staging and source tests.
param([Parameter(Mandatory)][ValidateSet('freeze','install','upgrade')][string]$Stage)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$source = (Resolve-Path 'build/Falcon_Ai_V14_4_Candidate').Path
$runtime = (Resolve-Path 'build/falcon_app_v144_runtime').Path
$appDir = Join-Path $env:LOCALAPPDATA 'Programs\Falcon Ai'
$installed = Join-Path $appDir 'Falcon Ai.exe'
$versionFile = Join-Path $appDir '_internal\RELEASE_VERSION.txt'
$helper = Join-Path $appDir '_internal\app_update_restart.ps1'
$data = Join-Path $env:LOCALAPPDATA 'FalconAI'

function Run-Checked($file, $arguments) {
    Write-Host ("Starting " + [IO.Path]::GetFileName($file) + " " + ($arguments -join " "))
    $p = Start-Process -FilePath $file -ArgumentList $arguments -PassThru
    if (!$p.WaitForExit(180000)) {
        $p.Refresh()
        Write-Host ("Window title: " + $p.MainWindowTitle)
        if ($p.MainWindowHandle -ne [IntPtr]::Zero) {
            Add-Type -AssemblyName UIAutomationClient
            $window = [System.Windows.Automation.AutomationElement]::FromHandle($p.MainWindowHandle)
            $visible = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                [System.Windows.Automation.Condition]::TrueCondition)
            $visible | Select-Object -First 15 | ForEach-Object { Write-Host $_.Current.Name }
        }
        $p.Kill()
        throw "Timed out running $file $arguments"
    }
    if ($p.ExitCode -ne 0) { throw "$file returned $($p.ExitCode)" }
}

function Test-Application($file) {
    foreach ($flag in @('--falcon-self-test','--falcon-diagnostics-self-test','--falcon-foundation-self-test',
                        '--falcon-money-self-test','--falcon-store-self-test','--falcon-shorts-self-test')) {
        Run-Checked $file $flag
    }
    $report = Get-ChildItem (Join-Path $data 'v13_5_diagnostics') -Filter 'check_*.json' |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $checks = @((Get-Content $report.FullName -Raw | ConvertFrom-Json).checks.PSObject.Properties)
    if ($checks.Count -ne 13 -or @($checks | Where-Object Value -ne 'present').Count) {
        throw 'Expected all 13 packaged diagnostics'
    }
}

if ($Stage -eq 'freeze') {
    $repo = (Resolve-Path '.').Path
    $argsList = @('--noconfirm','--clean','--windowed','--onedir','--name','Falcon Ai',
        '--distpath',(Join-Path $repo 'dist'),'--workpath',(Join-Path $repo 'build/pyinstaller'),
        '--specpath',(Join-Path $repo 'build/pyinstaller'),
        '--add-data',((Resolve-Path 'packaging/app_update_restart.ps1').Path + ';.'),
        '--add-data',($source + '\RELEASE_VERSION.txt;.'),
        '--add-data',($runtime + '\Falcon_Ai_Icon.png;.'),
        '--icon',($runtime + '\Falcon_Ai_Icon.ico'),
        '--hidden-import=winotify','--hidden-import=pyautogui','--hidden-import=PIL.Image',
        '--collect-all=pyautogui','--collect-all=playwright')
    foreach ($module in (Get-ChildItem $source -Filter '*.py' -File)) {
        $argsList += @('--add-data',($module.FullName + ';.'))
        if ($module.BaseName -ne 'sandbox_runner') { $argsList += "--hidden-import=$($module.BaseName)" }
    }
    $previousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = $source + [IO.Path]::PathSeparator + $runtime
    # Freeze from the staged application so checkout-only modules cannot shadow packaged modules.
    Push-Location $source
    try { python -P -m PyInstaller @argsList (Join-Path $runtime 'app_entry.py') }
    finally { Pop-Location; $env:PYTHONPATH = $previousPythonPath }
    Test-Application (Resolve-Path 'dist/Falcon Ai/Falcon Ai.exe').Path
    return
}

if ($Stage -eq 'install') {
    $compiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
    if (!(Test-Path $compiler)) { choco install innosetup -y --no-progress --limit-output }
    Copy-Item (Join-Path $runtime 'Falcon_Ai.iss') 'Falcon_Ai.iss'
    & $compiler 'Falcon_Ai.iss'
    Run-Checked (Resolve-Path 'output/Falcon_Ai_Setup.exe').Path '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
    if ((Get-Content $versionFile -Raw).Trim() -ne '14.4.0' -or !(Test-Path $helper)) { throw 'Clean install identity failed' }
    Test-Application $installed
    return
}

$setup = (Resolve-Path 'output/Falcon_Ai_Setup.exe').Path
$uninstaller = Get-ChildItem $appDir -Filter 'unins*.exe' -File | Select-Object -First 1
Run-Checked $uninstaller.FullName '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
$prior = gh api "repos/$env:GITHUB_REPOSITORY/releases/latest" | ConvertFrom-Json
if ($prior.tag_name -ne 'v14.3.2') { throw 'The public release changed. Recheck the upgrade baseline.' }
$asset = @($prior.assets | Where-Object name -eq 'Falcon_Ai_Setup.exe')
if ($asset.Count -ne 1 -or $asset[0].digest -notmatch '^sha256:[a-fA-F0-9]{64}$') { throw 'Prior release digest unavailable' }
$oldDir = Join-Path $env:RUNNER_TEMP 'falcon-prior'
New-Item $oldDir -ItemType Directory -Force | Out-Null
gh release download $prior.tag_name -R $env:GITHUB_REPOSITORY -p Falcon_Ai_Setup.exe -D $oldDir
$oldSetup = Join-Path $oldDir 'Falcon_Ai_Setup.exe'
if ('sha256:' + (Get-FileHash $oldSetup -Algorithm SHA256).Hash -ne $asset[0].digest) { throw 'Prior installer digest mismatch' }
Run-Checked $oldSetup '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
if ((Get-Content $versionFile -Raw).Trim() -ne '14.3.2' -or !(Test-Path $helper)) { throw 'Prior install failed' }

$update = Join-Path $data 'installer_updates\falcon_ai_1440_ci'
New-Item $update -ItemType Directory -Force | Out-Null
$keep = Join-Path $data 'ci_private_data_keep.txt'
$sentinel = [Guid]::NewGuid().ToString()
$sentinel | Set-Content $keep
$next = Join-Path $update 'Falcon_Ai_Setup.exe'
Copy-Item $setup $next
$log = Join-Path $data 'logs\app_installer_update.log'
if (Test-Path $log) { Remove-Item -LiteralPath $log }
Run-Checked 'powershell.exe' @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
    '-File',('"' + $helper + '"'),'-WaitPid','999999',
    '-Installer',('"' + $next + '"'),'-AppExe',('"' + $installed + '"'))
if ((Get-Content $keep -Raw).Trim() -ne $sentinel -or (Get-Content $versionFile -Raw).Trim() -ne '14.4.0') {
    throw 'Upgrade version or local data preservation failed'
}
$events = Get-Content $log -Raw
if (!$events.Contains('Installer exit code 0') -or !$events.Contains('New Falcon Ai application is running')) {
    throw 'Updater did not confirm automatic relaunch'
}
Test-Application $installed
if ((Get-Item $setup).Length -lt 5000000) { throw 'Installer unexpectedly small' }
(Get-FileHash $setup -Algorithm SHA256).Hash.ToLowerInvariant() | Set-Content 'output/Falcon_Ai_Setup.sha256' -Encoding ascii
git rev-parse HEAD | Set-Content 'output/SOURCE_COMMIT.txt' -Encoding ascii
Write-Host 'Windows clean install, 14.3.2 upgrade, relaunch, local data and packaged diagnostics passed.'
