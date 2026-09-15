"""Teste do pacote instalado, invocado pelo CI com PATH vazio."""
import json
import time
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication
from runtime import VERSION, find_tool, spawn


def command(arguments):
    process = spawn(arguments, stdout=-1, stderr=-1)
    try:
        output, errors = process.communicate(timeout=30)
    except BaseException:
        process.kill()
        process.communicate()
        raise
    if process.returncode:
        raise RuntimeError(errors.decode('utf-8', errors='replace'))
    return output


def run(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    report = {'version': VERSION, 'ok': False}
    try:
        from app import ConverterWindow
        ffmpeg, ffprobe = find_tool('ffmpeg'), find_tool('ffprobe')
        report['ffmpeg'] = str(ffmpeg)
        report['ffprobe'] = str(ffprobe)
        application = QApplication.instance() or QApplication([])
        application.setQuitOnLastWindowClosed(False)
        for suffix, codec in [('mp4', 'aac'), ('webm', 'vorbis')]:
            source = folder / f'reunião com espaços.{suffix}'
            command([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=duration=0.5',
                     '-c:a', codec, '-ac', '2', '-strict', '-2', source])
            window = ConverterWindow()
            window.show()
            window.select_source(source)
            window.start()
            deadline = time.monotonic() + 30
            while window.working and time.monotonic() < deadline:
                application.processEvents()
                time.sleep(0.01)
            if window.working:
                window.cancel()
                window.worker.join(timeout=10)
                raise RuntimeError('Tempo esgotado durante a conversão do pacote.')
            if window.output is None:
                raise RuntimeError(window.status.text())
            metadata = json.loads(command([ffprobe, '-v', 'error', '-show_streams',
                                          '-of', 'json', window.output]))
            stream = metadata['streams'][0]
            assert stream['codec_name'] == 'mp3'
            assert stream['sample_rate'] == '44100' and stream['channels'] == 2
            window.close()
            application.processEvents()
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    (folder / 'smoke-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1
