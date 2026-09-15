import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY') and os.name != 'nt':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from app import ConverterWindow
from converter import ConversionCancelled
from dialogs import file_chooser

application = QApplication.instance() or QApplication([])
application.setQuitOnLastWindowClosed(False)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / 'reunião com espaços.webm'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1',
                        '-c:a', 'libopus', str(self.source)], capture_output=True, check=True)
        self.window = ConverterWindow()
        self.window.show()
        self.addCleanup(self.cleanup_window)
        # A lógica dos seletores é automatizada; os diálogos do SO são verificados manualmente.
        def chooser(parent, **kwargs):
            dialog = file_chooser(parent, **kwargs)
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
            return dialog
        self.patcher = patch('app.file_chooser', side_effect=chooser)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def cleanup_window(self):
        if self.window.worker and self.window.worker.is_alive():
            self.window.cancel()
            self.window.worker.join(timeout=10)
        self.window._poll()
        self.window.close()
        self.window.deleteLater()
        application.processEvents()

    def wait_for(self, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            application.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        self.fail('A interface não atingiu o estado esperado.')

    def test_open_save_and_real_conversion(self):
        self.assertFalse(self.window.start_button.isEnabled())
        self.window.choose_source()
        chooser = self.window.chooser
        self.assertEqual(chooser.acceptMode(), QFileDialog.AcceptMode.AcceptOpen)
        self.assertTrue(chooser.isModal())
        self.assertIn('*.WEBM', chooser.nameFilters()[0])
        chooser.selectFile(str(self.source))
        chooser.accept()
        self.assertEqual(self.window.source, self.source)
        self.window.choose_destination()
        chooser = self.window.chooser
        self.assertEqual(chooser.acceptMode(), QFileDialog.AcceptMode.AcceptSave)
        chooser.selectFile(str(Path(self.directory.name) / 'áudio final'))
        chooser.accept()
        output = Path(self.directory.name) / 'áudio final.mp3'
        self.assertEqual(self.window.destination, output)
        self.window.start_button.click()
        self.assertFalse(self.window.source_row.button.isEnabled())
        self.wait_for(lambda: self.window.output is not None)
        self.assertEqual(self.window.output, output)
        self.assertGreater(output.stat().st_size, 0)
        self.assertEqual(self.window.bar.value(), 100)
        self.assertTrue(self.window.folder_button.isEnabled())
        self.assertFalse(self.window.cancel_button.isEnabled())

    def test_native_dialog_is_default(self):
        chooser = file_chooser(self.window)
        self.assertFalse(chooser.testOption(QFileDialog.Option.DontUseNativeDialog))
        chooser.deleteLater()

    def test_mp4_source_and_numbered_destination(self):
        source = Path(self.directory.name) / 'reunião.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1',
                        '-c:a', 'aac', str(source)], capture_output=True, check=True)
        source.with_suffix('.mp3').write_bytes(b'existing')
        self.window.select_source(source)
        self.assertEqual(self.window.destination.name, 'reunião-1.mp3')
        self.assertTrue(self.window.start_button.isEnabled())

    def test_unsupported_source_is_rejected(self):
        with patch('app.show_error') as error:
            self.window.select_source(self.source.with_suffix('.mkv'))
        error.assert_called_once()
        self.assertIsNone(self.window.source)

    def test_cancel_picker_preserves_selection(self):
        self.window.select_source(self.source)
        self.window.choose_source()
        self.window.chooser.reject()
        self.assertEqual(self.window.source, self.source)
        self.assertIsNone(self.window.chooser)

    def test_existing_save_target_is_rejected(self):
        self.window.select_source(self.source)
        existing = Path(self.directory.name) / 'ocupado.mp3'
        existing.write_bytes(b'original')
        original = self.window.destination
        self.window.choose_destination()
        self.window.chooser.selectFile(str(existing))
        with patch('app.show_error') as error:
            self.window.chooser.accept()
        error.assert_called_once()
        self.assertEqual(self.window.destination, original)
        self.assertEqual(existing.read_bytes(), b'original')

    @staticmethod
    def slow_conversion(source, destination, bitrate, cancelled, progress):
        progress(None)
        if cancelled.wait(5):
            raise ConversionCancelled()
        raise RuntimeError('O teste deveria cancelar a conversão.')

    def test_cancel_restores_controls(self):
        self.window.select_source(self.source)
        with patch('app.convert', side_effect=self.slow_conversion):
            self.window.start()
            self.wait_for(lambda: self.window.bar.maximum() == 0)
            self.window.cancel_button.click()
            self.wait_for(lambda: not self.window.working)
        self.assertEqual(self.window.status.text(), 'Conversão cancelada.')
        self.assertTrue(self.window.start_button.isEnabled())
        self.assertFalse(self.window.folder_button.isEnabled())

    def test_close_waits_for_worker_and_cancel(self):
        self.window.select_source(self.source)
        with patch('app.convert', side_effect=self.slow_conversion):
            self.window.start()
            self.window.close()
            self.assertTrue(self.window.isVisible())
            self.window.close_dialog.done(QMessageBox.StandardButton.No)
            self.assertFalse(self.window.closing)
            self.window.close()
            self.window.close_dialog.done(QMessageBox.StandardButton.Yes)
            self.wait_for(lambda: not self.window.isVisible())
        self.assertFalse(self.window.worker.is_alive())
        self.assertFalse(self.window.timer.isActive())

    def test_open_folder_uses_local_url(self):
        self.window.output = Path(self.directory.name) / 'áudio.mp3'
        with patch('app.QDesktopServices.openUrl', return_value=True) as open_url:
            self.window.open_folder()
        self.assertEqual(Path(open_url.call_args.args[0].toLocalFile()), self.window.output.parent)

    def test_conversion_failure_restores_controls(self):
        self.window.select_source(self.source)
        with patch('app.convert', side_effect=RuntimeError('falha')), patch('app.show_error') as error:
            self.window.start()
            self.wait_for(lambda: not self.window.working)
            error.assert_called_once()
        self.assertTrue(self.window.start_button.isEnabled())
        self.assertFalse(self.window.folder_button.isEnabled())


if __name__ == '__main__':
    unittest.main()
