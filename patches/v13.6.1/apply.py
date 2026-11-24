"""Rebuild Falcon V13.6.1 from verified V13.6 source without unsafe imports."""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[2]
source = REPO / 'build' / 'Falcon_AI_V13_6'
target = REPO / 'build' / 'Falcon_AI_V13_6_1'
if not (source / 'RELEASE_VERSION.txt').exists() or (source / 'RELEASE_VERSION.txt').read_text().strip() != '13.6.0':
    raise SystemExit('Verified V13.6 source must be built before applying this patch')
if target.exists():
    shutil.rmtree(target)
shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

def replace(rel, old, new):
    path = target / rel
    data = path.read_text(encoding='utf-8')
    if data.count(old) != 1:
        raise SystemExit(f'Patch anchor mismatch in {rel}: {old[:80]!r}, {data.count(old)} matches')
    path.write_text(data.replace(old, new, 1), encoding='utf-8')

old = """    Start-Process -FilePath 'cmd.exe' -ArgumentList ('/c "' + (Join-Path $Live 'START_HERE.bat') + '"') -WorkingDirectory $Live
    exit 0"""
new = """    # Relaunch without a visible console or stealing focus from games.
    $pythonw = Join-Path $Live '.venv\Scripts\pythonw.exe'
    $launcher = Join-Path $Live 'falcon_launcher.py'
    if (-not (Test-Path -LiteralPath $pythonw) -or
        -not (Test-Path -LiteralPath $launcher)) {
      throw 'Cannot restart Falcon: Windows Python environment or launcher missing'
    }
    $env:FALCON_RESTART_MINIMIZED = '1'
    $bootLog = Join-Path $home 'logs\v13_5_startup.log'
    $relaunchTime = Get-Date
    $child = Start-Process -FilePath $pythonw -ArgumentList ('"' + $launcher + '"') -WorkingDirectory $Live -PassThru
    $ready = $false
    for ($j = 0; $j -lt 36; $j++) {
      Start-Sleep -Milliseconds 500
      $child.Refresh()
      if ($child.HasExited) {
        throw ('Updated Falcon closed during restart (exit code ' + $child.ExitCode + ')')
      }
      if (Test-Path -LiteralPath $bootLog) {
        $logItem = Get-Item -LiteralPath $bootLog
        if ($logItem.LastWriteTime -ge $relaunchTime.AddSeconds(-1)) {
          $tail = Get-Content -LiteralPath $bootLog -Tail 36 -ErrorAction SilentlyContinue
          $started = $tail | Select-String -Pattern '\[BOOT\] Starting Falcon' | Select-Object -Last 1
          $gui = $tail | Select-String -Pattern '\[BOOT\] GUI ready' | Select-Object -Last 1
          if ($started -and $gui -and $gui.LineNumber -gt $started.LineNumber) {
            $ready = $true
            break
          }
        }
      }
    }
    if ($ready) {
      Log ('Falcon restarted in background successfully (PID ' + $child.Id + ')')
    } else {
      Log ('Falcon process running (PID ' + $child.Id + '), GUI startup still unconfirmed')
    }
    exit 0"""
replace('APPLY_RELEASE_UPDATE.ps1', old, new)
replace('APPLY_RELEASE_UPDATE.ps1',
"""    Move-Item -LiteralPath $backup -Destination $Live
    throw""",
"""    Move-Item -LiteralPath $backup -Destination $Live
    # Restore previous GUI after a failed relaunch, without opening CMD.
    try {
      $restorePython = Join-Path $Live '.venv\Scripts\pythonw.exe'
      $restoreLauncher = Join-Path $Live 'falcon_launcher.py'
      if ((Test-Path -LiteralPath $restorePython) -and
          (Test-Path -LiteralPath $restoreLauncher)) {
        $env:FALCON_RESTART_MINIMIZED = '1'
        Start-Process -FilePath $restorePython -ArgumentList ('"' + $restoreLauncher + '"') -WorkingDirectory $Live | Out-Null
        Log 'Previous Falcon relaunched after rollback'
      }
    } catch {
      Log ('Previous Falcon could not restart: ' + $_.Exception.Message)
    }
    throw""")
replace('falcon_launcher.py',
"""            root=tk.Tk()
            Falcon(root)
            print('[BOOT] GUI ready. Python startup completed.',file=log)""",
"""            root=tk.Tk()
            # An approved release update should not interrupt a full-screen game.
            restart_minimized = os.getenv('FALCON_RESTART_MINIMIZED') == '1'
            if restart_minimized:
                root.iconify()
            app = Falcon(root)
            if restart_minimized:
                root.after(1200, lambda: app.notifier.notify(
                    'Falcon AI updated', 'Falcon restarted successfully and is running in the background.',
                    kind='update'))
            print('[BOOT] GUI ready. Python startup completed.',file=log)""")
replace('release_updates.py', 'CURRENT_VERSION = (13, 6, 0)', 'CURRENT_VERSION = (13, 6, 1)')
for old, new in [('Falcon AI V13.6 — Command Center', 'Falcon AI V13.6.1 — Command Center'),
                 ('Falcon V13.6 ready.', 'Falcon V13.6.1 ready.'),
                 ('V13.6  /  LOCAL JARVIS', 'V13.6.1  /  LOCAL JARVIS')]:
    replace('falcon.py', old, new)
(target / 'RELEASE_VERSION.txt').write_text('13.6.1\n', encoding='utf-8')
for rel in ('tests/test_v135_permanent.py', 'tests/test_v131_updates.py'):
    path = target / rel
    value = path.read_text(encoding='utf-8')
    value = value.replace('(13,6,0)', '(13,6,1)').replace('13.6.0', '13.6.1')
    value = value.replace('Falcon_AI_V13_6/', 'Falcon_AI_V13_6_1/')
    path.write_text(value, encoding='utf-8')
(target/'tests'/'test_v1361_restart.py').write_text("""from pathlib import Path
import unittest
import release_updates

ROOT = Path(__file__).resolve().parents[1]

class RestartTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(release_updates.CURRENT_VERSION, (13, 6, 1))
        self.assertEqual((ROOT/'RELEASE_VERSION.txt').read_text().strip(), '13.6.1')
    def test_background_restart(self):
        ps=(ROOT/'APPLY_RELEASE_UPDATE.ps1').read_text()
        self.assertIn('Start-Process -FilePath $pythonw', ps)
        self.assertIn('Start-Process -FilePath $restorePython', ps)
        self.assertNotIn("Start-Process -FilePath 'cmd.exe'", ps)
        self.assertIn('Move-Item -LiteralPath $backup -Destination $Live', ps)
        self.assertIn('Get-Content -LiteralPath $bootLog', ps)
        launcher=(ROOT/'falcon_launcher.py').read_text()
        self.assertIn('root.iconify()', launcher)
        self.assertIn('Falcon AI updated', launcher)
        self.assertIn("kind='update'",launcher)
    def test_update_validation_remains(self):
        updates=(ROOT/'release_updates.py').read_text()
        self.assertIn('def verify_archive(', updates)
        self.assertIn('def schedule_install(', updates)

if __name__ == '__main__':
    unittest.main()
""", encoding='utf-8')
(target / 'README_V13_6_1.txt').write_text(
    'Falcon AI V13.6.1 — restart repair\n'
    'After approved releases, Falcon launches via pythonw.exe (no console), '
    'minimizes to the taskbar, and requests a Windows notification. '
    'An early startup exit triggers rollback and a relaunch of the previous release. '
    'Desktop behavior still needs live Windows verification. '
    'Manual launcher: %LOCALAPPDATA%\\Programs\\FalconAI\\START_HERE.bat. '
    'Helper log: %LOCALAPPDATA%\\FalconAI\\release_update.log.\n',
    encoding='utf-8')
print('Built Falcon V13.6.1 source with quiet relaunch; no new privileges')
