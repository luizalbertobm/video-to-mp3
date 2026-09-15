# Build with: python -m PyInstaller --clean --noconfirm video-to-mp3.spec
from pathlib import Path
import sys

root = Path(SPECPATH)
suffix = '.exe' if sys.platform == 'win32' else ''
binaries = [(str(root / 'vendor' / 'bin' / (name + suffix)), 'bin')
            for name in ('ffmpeg', 'ffprobe')]
for binary, _ in binaries:
    if not Path(binary).is_file():
        raise SystemExit('Run scripts/build-media.sh before packaging.')
data = [(str(root / 'assets' / 'icon.png'), 'assets'),
        (str(root / 'licenses'), 'licenses'),
        (str(root / 'THIRD_PARTY_NOTICES.md'), 'licenses'),
        (str(root / 'vendor' / 'licenses'), 'licenses/media'),
        (str(root / 'vendor' / 'ffmpeg-build.txt'), 'licenses/media'),
        (str(root / 'vendor' / 'SHA256SUMS'), 'licenses/media')]
a = Analysis([str(root / 'app.py')], pathex=[str(root)], binaries=binaries, datas=data,
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                       'PySide6.QtQml', 'PySide6.QtQuick'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='video-to-mp3',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False,
          icon=str(root / 'assets' / ('icon.ico' if sys.platform == 'win32' else 'icon.icns')),
          version=str(root / 'assets' / 'windows-version.txt') if sys.platform == 'win32' else None,
          target_arch=None, codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='video-to-mp3')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='Vídeo para MP3.app', icon=str(root / 'assets' / 'icon.icns'),
                 bundle_identifier='net.beecoders.WebmToMp3', version='1.0.0',
                 info_plist={'NSHighResolutionCapable': True, 'LSMinimumSystemVersion': '13.0',
                             'CFBundleDisplayName': 'Vídeo para MP3', 'CFBundleShortVersionString': '1.0.0'})
