# Third-party software

The release contains Python 3.12, Qt/PySide6/shiboken6 6.8.3 and FFmpeg 8.1.1
with LAME 3.100. These components retain their respective licenses.

- Python: PSF license and third-party notices in `licenses/Python.txt`.
  Source: https://www.python.org/downloads/source/
- Qt, PySide6 and shiboken6: LGPLv3, with LGPL and GPL license texts in
  `licenses/Qt-LGPL-3.0.txt` and `licenses/Qt-GPL-3.0.txt`.
  Exact upstream sources:
  https://download.qt.io/archive/qt/6.8/6.8.3/single/qt-everywhere-src-6.8.3.tar.xz
  https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/
  Qt is dynamically loaded: its libraries remain separate in the application
  directory (Contents/Frameworks on macOS). You may replace/relink LGPL libraries
  and debug such modifications under their licenses. Modified macOS bundles
  may need a new ad-hoc signature. This app imposes no restriction on those rights.
- FFmpeg: LGPL 2.1 or later; LAME: LGPL 2.0 or later. This build does not enable
  GPL or nonfree components. Exact source archives, build script and FFmpeg
  configuration log are included in `media-sources/`. License texts, binary
  hashes and configuration are included in the application's `licenses/media/`.
  Official projects: https://ffmpeg.org/ and https://lame.sourceforge.io/.
  FFmpeg and LAME are linked together statically and run as a separate process;
  rebuild them with the included script and replace `bin/ffmpeg` and `bin/ffprobe`
  (or the .exe files). No network protocols are enabled in this FFmpeg build.
- The PyInstaller bootloader is distributed under GPL with the bootloader
  exception, which permits distributing bundled applications under their own
  terms. See `licenses/PyInstaller.txt` and https://pyinstaller.org/.

Additional dependency notices shipped by wheels are collected during packaging.
The source archives accompany each release; do not remove them when redistributing.
