"""Extract the deliverable and launch it elsewhere with no FFmpeg/Python on PATH."""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import shutil

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from runtime import VERSION

system = {'win32': 'windows', 'darwin': 'macos', 'linux': 'linux'}[sys.platform]
arch = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'x64'
name = f'video-to-mp3-{VERSION}-{system}-{arch}'
archive = root / 'dist' / (name + ('.tar.gz' if system == 'linux' else '.zip'))
with tempfile.TemporaryDirectory(prefix='video-mp3-package-') as directory:
    folder = Path(directory)
    if system == 'macos':
        subprocess.run(['ditto', '-x', '-k', str(archive), str(folder)], check=True)
    else:
        shutil.unpack_archive(archive, folder)
    executable = folder / name / ('video-to-mp3.exe' if system == 'windows' else 'video-to-mp3')
    if system == 'macos':
        executable = folder / name / 'Vídeo para MP3.app' / 'Contents' / 'MacOS' / 'video-to-mp3'
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(folder / name / 'Vídeo para MP3.app')], check=True)
    result = folder / 'resultado com espaços'
    env = dict(os.environ, PATH='', PYTHONPATH='', QT_QPA_PLATFORM=os.environ.get('QT_QPA_PLATFORM', 'offscreen'))
    completed = subprocess.run([str(executable), '--smoke-test', str(result)], cwd=folder,
                               env=env, timeout=90, capture_output=True)
    report = result / 'smoke-result.json'
    if report.exists():
        text = report.read_text(encoding='utf-8')
        print(text)
        data = json.loads(text)
    else:
        data = {'ok': False}
    if completed.returncode or not data['ok']:
        raise SystemExit(f'Package smoke test failed: {completed.returncode}\n{completed.stderr!r}')
