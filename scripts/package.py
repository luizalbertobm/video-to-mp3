"""Package a native onedir build and keep source/license materials alongside it."""
import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from runtime import VERSION


def main():
    os.chdir(ROOT)
    if sys.platform == 'darwin':
        os.environ['MACOSX_DEPLOYMENT_TARGET'] = '13.0'
    # Preserve third-party license files that wheels make available.
    target = ROOT / 'build' / 'wheel-licenses'
    target.mkdir(parents=True, exist_ok=True)
    for name in ('PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'PyInstaller'):
        dist = importlib.metadata.distribution(name)
        for entry in dist.files or []:
            if any(term in entry.name.lower() for term in ('license', 'copying')):
                source = Path(dist.locate_file(entry))
                if source.is_file():
                    shutil.copy2(source, target / f'{name}-{entry.name}')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm',
                    'video-to-mp3.spec'], check=True)
    system = {'win32': 'windows', 'darwin': 'macos', 'linux': 'linux'}[sys.platform]
    arch = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'x64'
    name = f'video-to-mp3-{VERSION}-{system}-{arch}'
    stage = ROOT / 'build' / 'release' / name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    if sys.platform == 'darwin':
        shutil.copytree(ROOT / 'dist' / 'Vídeo para MP3.app', stage / 'Vídeo para MP3.app', symlinks=True)
    else:
        shutil.copytree(ROOT / 'dist' / 'video-to-mp3', stage, dirs_exist_ok=True)
    shutil.copytree(ROOT / 'vendor' / 'sources', stage / 'media-sources')
    shutil.copytree(target, stage / 'wheel-licenses')
    for filename in ('README.md', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(ROOT / filename, stage / filename)
    if sys.platform == 'linux':
        shutil.copy2(ROOT / 'install.sh', stage)
        shutil.copy2(ROOT / 'video-to-mp3.desktop.in', stage)
        (stage / 'assets').mkdir(exist_ok=True)
        shutil.copy2(ROOT / 'assets' / 'icon.png', stage / 'assets')
    base = ROOT / 'dist' / name
    if sys.platform == 'darwin':
        # ditto preserves bundle symlinks and executable permissions.
        archive = str(base) + '.zip'
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(stage), archive], check=True)
    elif sys.platform == 'linux':
        archive = str(base) + '.tar.gz'
        with tarfile.open(archive, 'w:gz', compresslevel=6) as output:
            output.add(stage, arcname=stage.name)
    else:
        archive = shutil.make_archive(str(base), 'zip', root_dir=stage.parent, base_dir=stage.name)
    archive = Path(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + '.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    print(archive)


if __name__ == '__main__':
    main()
