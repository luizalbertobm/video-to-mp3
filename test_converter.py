import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from converter import ConversionCancelled, ConversionError, convert


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.destination = self.folder / "reunião convertida.mp3"
        self.source = self.make_source("reunião com espaços.webm", "libopus")

    def make_source(self, name, codec, duration=2):
        path = self.folder / name
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-c:a", codec, str(path),
        ], check=True, capture_output=True)
        return path

    def run_conversion(self, **kwargs):
        return convert(self.source, self.destination, 128,
                       kwargs.get("cancelled", threading.Event()),
                       kwargs.get("progress", lambda value: None))

    def assert_valid_mp3(self, updates):
        metadata = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate:format=duration",
            "-of", "json", str(self.destination),
        ]))
        self.assertEqual(metadata["streams"][0]["codec_name"], "mp3")
        self.assertEqual(metadata["streams"][0]["sample_rate"], "44100")
        self.assertAlmostEqual(float(metadata["format"]["duration"]), 2, delta=0.15)
        self.assertEqual(updates[-1], 100)
        self.assertFalse(list(self.folder.glob(".video-to-mp3-*")))

    def test_real_conversion_preserves_source_and_creates_valid_mp3(self):
        original = self.source.read_bytes()
        updates = []
        self.assertEqual(self.run_conversion(progress=updates.append), self.destination)
        self.assertEqual(self.source.read_bytes(), original)
        self.assert_valid_mp3(updates)

    def test_real_mp4_conversion_creates_valid_mp3(self):
        self.source = self.make_source("reunião gravada.mp4", "aac")
        original = self.source.read_bytes()
        updates = []
        self.assertEqual(self.run_conversion(progress=updates.append), self.destination)
        self.assertEqual(self.source.read_bytes(), original)
        self.assert_valid_mp3(updates)

    def test_unsupported_extension_is_rejected(self):
        self.source = self.make_source("reunião.mkv", "libopus")
        with self.assertRaisesRegex(ConversionError, "WebM ou MP4"):
            self.run_conversion()
        self.assertFalse(self.destination.exists())

    def test_existing_destination_is_preserved(self):
        self.destination.write_bytes(b"existing audio")
        with self.assertRaises(ConversionError):
            self.run_conversion()
        self.assertEqual(self.destination.read_bytes(), b"existing audio")

    def test_destination_created_during_conversion_is_preserved(self):
        def occupy_destination(value):
            if not self.destination.exists():
                self.destination.write_bytes(b"other application")
        with self.assertRaises(ConversionError):
            self.run_conversion(progress=occupy_destination)
        self.assertEqual(self.destination.read_bytes(), b"other application")
        self.assertFalse(list(self.folder.glob(".video-to-mp3-*")))

    def test_cancel_during_conversion_removes_partial_output(self):
        cancelled = threading.Event()
        def cancel_at_progress(value):
            cancelled.set()
        with self.assertRaises(ConversionCancelled):
            self.run_conversion(cancelled=cancelled, progress=cancel_at_progress)
        self.assertFalse(self.destination.exists())
        self.assertFalse(list(self.folder.glob(".video-to-mp3-*")))

    def test_video_without_audio_is_rejected(self):
        self.source = self.folder / "silent.webm"
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=size=32x32:duration=0.1",
            "-c:v", "libvpx", "-an", str(self.source),
        ], check=True, capture_output=True)
        with self.assertRaisesRegex(ConversionError, "áudio"):
            self.run_conversion()
        self.assertFalse(self.destination.exists())

    def test_invalid_source_is_rejected(self):
        self.source.write_bytes(b"not a webm")
        with self.assertRaises(ConversionError):
            self.run_conversion()
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
