"""Verified GitHub installer updates for the packaged Falcon Ai Windows application.

Only trusted public GitHub Releases, verified size + SHA256, explicit user
consent. Data under LOCALAPPDATA/FalconAI remains untouched by installs.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

CURRENT_VERSION = (13, 7, 0)
ASSET_NAME = 'Falcon_Ai_Setup.exe'
MAX_INSTALLER = 350 * 1024 * 1024
LOCAL = Path(os.getenv('LOCALAPPDATA') or Path.home())
DATA = LOCAL / 'FalconAI'
CACHE = DATA / 'installer_updates'
CHANNEL = DATA / 'release_channel.json'
DEFAULT_REPO = 'Falcomam/FalconAI-Releases'
REPO_RE = re.compile(r'^[a-zA-Z\d][a-zA-Z\d._-]{0,98}/[a-zA-Z\d][a-zA-Z\d._-]{0,98}$')
VER_RE = re.compile(r'^v?(\d+)\.(\d+)(?:\.(\d+))?$', re.I)
SHA_RE = re.compile(r'^sha256:([a-fA-F0-9]{64})$')

class UpdateError(RuntimeError):
    pass

def parse_version(value):
    match = VER_RE.fullmatch(str(value or '').strip())
    if not match:
        raise UpdateError('Unexpected GitHub release version')
    return tuple(int(match[i] or 0) for i in (1, 2, 3))

def read_channel():
    try:
        candidate = json.loads(CHANNEL.read_text(encoding='utf-8')).get('github_repo')
        if isinstance(candidate, str) and REPO_RE.fullmatch(candidate):
            return candidate
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return DEFAULT_REPO

def set_channel(repo):
    if not isinstance(repo, str) or not REPO_RE.fullmatch(repo.strip()):
        raise UpdateError('Release channel must be owner/repo')
    repo = repo.strip()
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = CHANNEL.with_suffix('.tmp')
    tmp.write_text(json.dumps({'github_repo': repo}, indent=2), encoding='utf-8')
    tmp.replace(CHANNEL)
    return repo

def _get(req, limit, timeout, opener=urllib.request.urlopen):
    with opener(req, timeout=timeout) as resp:
        payload = resp.read(limit + 1)
    if len(payload) > limit:
        raise UpdateError('Release download exceeded safety size limit')
    return payload

def check_latest(repo=None, *, opener=urllib.request.urlopen):
    repo = repo or read_channel()
    if not REPO_RE.fullmatch(repo):
        raise UpdateError('Untrusted GitHub release channel')
    req = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/releases/latest',
        headers={'Accept':'application/vnd.github+json',
                 'User-Agent':'FalconAi-WindowsUpdater/13.7',
                 'X-GitHub-Api-Version':'2022-11-28'})
    try:
        data = json.loads(_get(req, 180000, 20, opener))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise UpdateError('Could not read GitHub release: ' + str(exc)[:180]) from exc
    if not isinstance(data, dict) or data.get('draft') or data.get('prerelease'):
        raise UpdateError('No eligible stable release found')
    version = parse_version(data.get('tag_name'))
    if version <= CURRENT_VERSION:
        return None
    for asset in data.get('assets', []):
        if not isinstance(asset, dict) or asset.get('name') != ASSET_NAME:
            continue
        sha = SHA_RE.fullmatch(asset.get('digest') or '')
        url = asset.get('browser_download_url')
        size = asset.get('size')
        expected = f'https://github.com/{repo}/releases/download/{data["tag_name"]}/{ASSET_NAME}'
        if not sha or type(size) is not int or not 1_000_000 <= size <= MAX_INSTALLER or url != expected:
            raise UpdateError('Installer release is missing a trusted SHA256 digest or URL')
        return {'repo':repo, 'version':version, 'tag':data['tag_name'],
                'url':url, 'digest':sha[1].lower(), 'size':size,
                'notes':str(data.get('body') or '')[:1200]}
    raise UpdateError('Latest stable release does not include a verified Falcon Ai installer')

def download_verified(release, *, opener=urllib.request.urlopen):
    req = urllib.request.Request(release['url'], headers={'User-Agent':'FalconAi-WindowsUpdater/13.7'})
    payload = _get(req, MAX_INSTALLER, 180, opener)
    if len(payload) != release['size'] or hashlib.sha256(payload).hexdigest() != release['digest']:
        raise UpdateError('Installer checksum mismatch: no update installed')
    if not payload.startswith(b'MZ'):
        raise UpdateError('Downloaded installer is not a Windows executable')
    return payload

def stage_update(raw, expected_version, *, app=None):
    if not isinstance(raw, bytes) or not raw.startswith(b'MZ') or len(raw) > MAX_INSTALLER:
        raise UpdateError('Invalid installer data')
    CACHE.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='falcon_ai_', dir=str(CACHE)))
    try:
        exe = folder / ASSET_NAME
        with exe.open('xb') as file:
            file.write(raw)
        return exe
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise

def _trusted_stage(stage):
    path = Path(stage).resolve()
    if path.name != ASSET_NAME or not path.parent.name.startswith('falcon_ai_') or path.parent.parent != CACHE.resolve():
        raise UpdateError('Refusing an installer outside the trusted cache')
    return path

def discard_stage(stage, *, app=None):
    path = _trusted_stage(stage)
    if path.parent.exists():
        shutil.rmtree(path.parent)

def schedule_install(stage, *, app=None, process_id=None):
    if sys.platform != 'win32':
        raise UpdateError('Falcon Ai installer updates require Windows')
    exe = _trusted_stage(stage)
    if not exe.is_file() or exe.is_symlink():
        raise UpdateError('Verified installer is missing')
    if not getattr(sys, 'frozen', False):
        raise UpdateError('Use the installed Falcon Ai application to update')
    installed_exe = Path(sys.executable).resolve()
    if installed_exe.name.casefold() != 'falcon ai.exe':
        raise UpdateError('Installed Falcon Ai executable not found')
    bundled_helper = Path(getattr(sys, '_MEIPASS', installed_exe.parent)) / 'app_update_restart.ps1'
    if not bundled_helper.is_file():
        raise UpdateError('Signed installer update helper missing')
    copied_helper = exe.parent / 'app_update_restart.ps1'
    shutil.copyfile(bundled_helper, copied_helper)
    if process_id is not None and (type(process_id) is not int or process_id <= 0):
        raise UpdateError('Invalid Falcon process ID')
    args = ['powershell.exe', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(copied_helper),
            '-WaitPid', str(process_id or os.getpid()),
            '-Installer', str(exe), '-AppExe', str(installed_exe)]
    # Child survives the closing GUI. Stdout/stderr are not inherited.
    flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    with open(os.devnull, 'wb') as sink:
        subprocess.Popen(args, cwd=str(exe.parent), creationflags=flags,
                         stdin=subprocess.DEVNULL, stdout=sink, stderr=sink,
                         close_fds=True)
    return True
