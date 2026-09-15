import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from converter import ConversionCancelled, ConversionError, _capture, _publish, convert
from runtime import find_tool
import runtime


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.temporary = self.root / 'temporary.mp3'
        self.destination = self.root / 'final.mp3'
        self.temporary.write_bytes(b'audio' * 300_000)
        self.cancelled = threading.Event()

    def test_exfat_fallback(self):
        with patch('converter.os.link', side_effect=OSError(errno.EOPNOTSUPP, 'unsupported')):
            _publish(self.temporary, self.destination, self.cancelled)
        self.assertEqual(self.destination.read_bytes(), self.temporary.read_bytes())

    def test_windows_exfat_not_supported_error(self):
        error = OSError(errno.EINVAL, 'unsupported Windows filesystem')
        error.winerror = 50
        with patch('converter.os.link', side_effect=error):
            _publish(self.temporary, self.destination, self.cancelled)
        self.assertEqual(self.destination.read_bytes(), self.temporary.read_bytes())

    def test_copy_failure_removes_partial_output(self):
        original_open = Path.open
        destination = self.destination
        class FullDisk:
            def __init__(self, stream):
                self.stream = stream
            def fileno(self):
                return self.stream.fileno()
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.stream.close()
            def write(self, chunk):
                self.stream.write(chunk[:100])
                raise OSError(errno.ENOSPC, 'full')
        def open_file(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            return FullDisk(stream) if path == destination else stream
        with patch('converter.os.link', side_effect=OSError(errno.EOPNOTSUPP, 'unsupported')):
            with patch.object(Path, 'open', open_file), self.assertRaises(OSError):
                _publish(self.temporary, self.destination, self.cancelled)
        self.assertFalse(self.destination.exists())

    def test_fallback_never_overwrites(self):
        self.destination.write_bytes(b'other app')
        with patch('converter.os.link', side_effect=OSError(errno.EPERM, 'unsupported')):
            with self.assertRaises(FileExistsError):
                _publish(self.temporary, self.destination, self.cancelled)
        self.assertEqual(self.destination.read_bytes(), b'other app')

    def test_cancellation_during_copy_removes_owned_output(self):
        original_open = Path.open
        event = self.cancelled
        temporary = self.temporary
        class CancelReader:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.stream.close()
            def read(self, size):
                data = self.stream.read(size)
                event.set()
                return data
        def open_file(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            return CancelReader(stream) if path == temporary else stream
        with patch('converter.os.link', side_effect=OSError(errno.EOPNOTSUPP, 'unsupported')):
            with patch.object(Path, 'open', open_file), self.assertRaises(ConversionCancelled):
                _publish(self.temporary, self.destination, event)
        self.assertFalse(self.destination.exists())

    def test_cancel_capture_reaps_process(self):
        processes = []
        def spawn(*args, **kwargs):
            process = subprocess.Popen(*args, **kwargs)
            processes.append(process)
            self.cancelled.set()
            return process
        with patch('converter.spawn', side_effect=spawn), self.assertRaises(ConversionCancelled):
            _capture([sys.executable, '-c', 'import time; time.sleep(30)'], self.cancelled)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdout.closed)

    def test_capture_timeout_reaps_process(self):
        processes = []
        def spawn(*args, **kwargs):
            process = subprocess.Popen(*args, **kwargs)
            processes.append(process)
            return process
        with patch('converter.spawn', side_effect=spawn), self.assertRaisesRegex(ConversionError, 'demorou'):
            _capture([sys.executable, '-c', 'import time; time.sleep(30)'], self.cancelled, timeout=0.05)
        self.assertIsNotNone(processes[0].poll())

    def test_frozen_uses_bundled_tools_without_path_fallback(self):
        folder = self.root / 'bin'
        folder.mkdir()
        binary = folder / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
        binary.touch()
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(self.root), create=True):
            with patch('runtime.shutil.which') as which:
                self.assertEqual(find_tool('ffmpeg'), binary.resolve())
                with self.assertRaises(FileNotFoundError):
                    find_tool('ffprobe')
                which.assert_not_called()

    def test_windows_subprocess_has_no_console(self):
        with patch('runtime.os.name', 'nt'), patch('runtime.subprocess.CREATE_NO_WINDOW', 0x08000000, create=True):
            with patch('runtime.subprocess.Popen') as popen:
                runtime.spawn(['ffmpeg', '-version'])
        self.assertEqual(popen.call_args.kwargs['creationflags'], 0x08000000)
        self.assertNotIn('shell', popen.call_args.kwargs)


class ConversionEdgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'entrada com acentuação.mp4'
        self.destination = self.root / 'áudio.mp3'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=0.3',
                        '-c:a', 'aac', str(self.source)], check=True, capture_output=True)

    def run_conversion(self, bitrate=128, progress=lambda value: None):
        return convert(self.source, self.destination, bitrate, threading.Event(), progress)

    def test_all_bitrates(self):
        for bitrate in (64, 128, 192, 320):
            with self.subTest(bitrate=bitrate):
                self.run_conversion(bitrate)
                data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                                                           '-of', 'json', str(self.destination)]))['streams'][0]
                self.assertEqual(data['channels'], 2)
                self.assertEqual(data['sample_rate'], '44100')
                self.assertEqual(int(data['bit_rate']), bitrate * 1000)
                self.destination.unlink()

    def test_missing_duration(self):
        real_capture = _capture
        def capture(args, *rest, **kwargs):
            if '-show_entries' in args:
                return 0, '{"streams":[{"codec_type":"audio"}]}', ''
            return real_capture(args, *rest, **kwargs)
        updates = []
        with patch('converter._capture', side_effect=capture):
            self.run_conversion(progress=updates.append)
        self.assertIsNone(updates[0])
        self.assertEqual(updates[-1], 100)

    def test_missing_encoder(self):
        with patch('converter._capture', return_value=(0, ' A..... aac', '')):
            with self.assertRaisesRegex(ConversionError, 'libmp3lame'):
                self.run_conversion()
        self.assertFalse(self.destination.exists())

    def test_missing_tool(self):
        with patch('converter.find_tool', side_effect=FileNotFoundError('ffprobe não encontrado')):
            with self.assertRaisesRegex(ConversionError, 'ffprobe'):
                self.run_conversion()

    def test_permission_and_disk_full(self):
        for error, message in [(PermissionError(errno.EACCES, 'denied'), 'permissão'),
                               (OSError(errno.ENOSPC, 'full'), 'espaço')]:
            with self.subTest(message=message), patch('converter.os.link', side_effect=error):
                with self.assertRaisesRegex(ConversionError, message):
                    self.run_conversion()
                self.assertFalse(self.destination.exists())
                self.assertFalse(list(self.root.glob('.video-to-mp3-*')))


if __name__ == '__main__':
    unittest.main()
