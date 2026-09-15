import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app import ConverterWindow, Gtk
from converter import ConversionCancelled


@unittest.skipUnless(Gtk.init_check()[0], 'A verificação da interface requer uma sessão gráfica.')
class NativeInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / 'reunião com espaços.webm'
        subprocess.run([
            'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1',
            '-c:a', 'libopus', str(self.source),
        ], capture_output=True, check=True)
        self.window = ConverterWindow()
        self.window.show_all()
        self.addCleanup(self.window.destroy)

    def wait_for(self, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            if predicate():
                return
            time.sleep(0.02)
        self.fail('A interface não atingiu o estado esperado.')

    def test_native_open_save_and_real_conversion(self):
        self.assertFalse(self.window.start_button.get_sensitive())
        self.window.choose_source()
        chooser = self.window.chooser
        self.assertIsInstance(chooser, Gtk.FileChooserNative)
        self.assertEqual(chooser.get_action(), Gtk.FileChooserAction.OPEN)
        self.assertTrue(chooser.get_modal())
        file_filter = chooser.list_filters()[0]
        for name, accepted in [('gravação.webm', True), ('GRAVAÇÃO.WEBM', True),
                               ('gravação.mp4', True), ('GRAVAÇÃO.MP4', True),
                               ('outro.txt', False), ('gravação.mkv', False)]:
            info = Gtk.FileFilterInfo()
            info.contains = Gtk.FileFilterFlags.DISPLAY_NAME
            info.display_name = name
            self.assertEqual(file_filter.filter(info), accepted)
        chooser.set_filename(str(self.source))
        self.wait_for(lambda: chooser.get_filename() == str(self.source))
        chooser.emit('response', Gtk.ResponseType.ACCEPT)
        self.assertEqual(self.window.source, self.source)
        self.assertEqual(self.window.destination, self.source.with_suffix('.mp3'))
        self.window.choose_destination()
        chooser = self.window.chooser
        self.assertIsInstance(chooser, Gtk.FileChooserNative)
        self.assertEqual(chooser.get_action(), Gtk.FileChooserAction.SAVE)
        chooser.set_current_folder(self.directory.name)
        chooser.set_current_name('áudio final')
        self.wait_for(lambda: chooser.get_filename() == str(Path(self.directory.name) / 'áudio final'))
        chooser.emit('response', Gtk.ResponseType.ACCEPT)
        output = Path(self.directory.name) / 'áudio final.mp3'
        self.assertEqual(self.window.destination, output)
        self.window.start_button.clicked()
        self.assertFalse(self.window.source_row.button.get_sensitive())
        self.wait_for(lambda: self.window.output is not None)
        self.assertEqual(self.window.output, output)
        self.assertGreater(output.stat().st_size, 0)
        self.assertEqual(self.window.bar.get_fraction(), 1)
        self.assertTrue(self.window.folder_button.get_sensitive())
        self.assertFalse(self.window.cancel_button.get_sensitive())

    def test_mp4_source_is_accepted(self):
        source = Path(self.directory.name) / 'reunião.mp4'
        subprocess.run([
            'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1',
            '-c:a', 'aac', str(source),
        ], capture_output=True, check=True)
        self.window.select_source(source)
        self.assertEqual(self.window.source, source)
        self.assertEqual(self.window.destination, source.with_suffix('.mp3'))
        self.assertTrue(self.window.start_button.get_sensitive())

    def test_unsupported_source_is_rejected(self):
        source = Path(self.directory.name) / 'reunião.mkv'
        subprocess.run([
            'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1',
            '-c:a', 'libopus', str(source),
        ], capture_output=True, check=True)
        with patch('app.show_error') as error:
            self.window.select_source(source)
        self.assertTrue(error.called)
        self.assertIsNone(self.window.source)

    def test_cancel_picker_preserves_selection(self):
        self.window.select_source(self.source)
        self.window.choose_source()
        self.window.chooser.emit('response', Gtk.ResponseType.CANCEL)
        self.assertEqual(self.window.source, self.source)
        self.assertIsNone(self.window.chooser)

    def test_cancel_restores_controls(self):
        self.window.select_source(self.source)
        entered = threading.Event()

        def slow_conversion(source, destination, bitrate, cancelled, progress):
            entered.set()
            if cancelled.wait(5):
                raise ConversionCancelled()
            raise RuntimeError('O teste deveria cancelar a conversão.')

        with patch('app.convert', side_effect=slow_conversion):
            self.window.start()
            self.wait_for(entered.is_set)
            self.window.cancel_button.clicked()
            self.wait_for(lambda: not self.window.working)
        self.assertEqual(self.window.status.get_text(), 'Conversão cancelada.')
        self.assertTrue(self.window.start_button.get_sensitive())
        self.assertFalse(self.window.folder_button.get_sensitive())
        self.assertFalse(self.source.with_suffix('.mp3').exists())


if __name__ == '__main__':
    unittest.main()
