#!/usr/bin/env python3
"""Conversor local de WebM/MP4 para MP3, para Linux, macOS e Windows."""
import os
import queue
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox

from converter import SOURCE_EXTENSIONS, ConversionCancelled, convert
from dialogs import file_chooser, show_error
from runtime import APP_ID, APP_NAME, VERSION
from ui import build_window


class ConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.source = self.destination = self.output = self.worker = None
        self.cancelled = threading.Event()
        self.events = queue.Queue()
        self.closing = self.working = False
        self.chooser = self.close_dialog = None
        build_window(self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(100)

    def choose_source(self):
        self._choose(False)

    def choose_destination(self):
        self._choose(True)

    def _choose(self, save):
        if self.chooser or self.working:
            return
        dialog = self.chooser = file_chooser(self, save=save)
        current = self.destination if save else self.source
        if current:
            dialog.setDirectory(str(current.parent))
            if save:
                dialog.selectFile(current.name)
        elif save:
            dialog.selectFile('reuniao.mp3')
        dialog.finished.connect(lambda result: self._file_selected(dialog, result, save))
        dialog.open()

    def _file_selected(self, dialog, result, save):
        paths = dialog.selectedFiles() if result == QDialog.DialogCode.Accepted else []
        dialog.deleteLater()
        self.chooser = None
        if not paths:
            return
        if save:
            target = Path(paths[0])
            if target.suffix.lower() != '.mp3':
                target = Path(str(target) + '.mp3')
            if os.path.lexists(target):
                show_error(self, 'Esse arquivo já existe', 'Escolha outro nome. Arquivos existentes não são sobrescritos.')
                return
            self.destination = target
            self.destination_row.set_path(target)
            self._reset_result()
        else:
            self.select_source(Path(paths[0]))

    def select_source(self, source):
        source = source.absolute()
        if source.suffix.lower() not in SOURCE_EXTENSIONS or not source.is_file():
            show_error(self, 'Arquivo inválido', 'Selecione uma gravação no formato WebM ou MP4.')
            return
        self.source = source
        target = source.with_suffix('.mp3')
        number = 1
        while os.path.lexists(target):
            target = source.with_name(f'{source.stem}-{number}.mp3')
            number += 1
        self.destination = target
        self.source_row.set_path(source)
        self.destination_row.set_path(target)
        self._reset_result()
        self._busy(False)

    def _reset_result(self):
        self.output = None
        self.folder_button.setEnabled(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFormat('Pronto para converter')
        self.status.setText('Confira o destino e clique em Converter para MP3.')
        self.status.setToolTip('')

    def _busy(self, busy):
        self.working = busy
        self.source_row.button.setEnabled(not busy)
        self.destination_row.button.setEnabled(not busy and self.source is not None)
        self.quality.setEnabled(not busy)
        self.start_button.setEnabled(not busy and self.source is not None)
        self.cancel_button.setEnabled(busy)

    def start(self):
        if self.working or not self.source or not self.destination:
            return
        source, destination = self.source, self.destination
        bitrate = self.quality.currentData()
        self.cancelled.clear()
        self.output = None
        self.folder_button.setEnabled(False)
        self._busy(True)
        self.bar.setRange(0, 0)
        self.bar.setFormat('Analisando…')
        self.status.setText('Analisando a gravação…')

        def work():
            try:
                output = convert(source, destination, bitrate, self.cancelled,
                                 lambda value: self.events.put(('progress', value)))
                self.events.put(('done', output))
            except ConversionCancelled:
                self.events.put(('cancelled', None))
            except Exception as error:
                self.events.put(('error', str(error)))

        self.worker = threading.Thread(target=work)
        self.worker.start()

    def _poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'progress':
                    self.status.setText('Cancelando…' if self.cancelled.is_set() else 'Convertendo o áudio…')
                    self.bar.setRange(0, 0 if value is None else 100)
                    self.bar.setFormat('Convertendo…' if value is None else f'{value:.0f}%')
                    if value is not None:
                        self.bar.setValue(round(value))
                else:
                    self._finish(kind, value)
        except queue.Empty:
            pass
        if self.closing and not (self.worker and self.worker.is_alive()):
            self.close()

    def _finish(self, kind, value):
        self._busy(False)
        self.bar.setRange(0, 100)
        if kind == 'done':
            self.output = value
            self.bar.setValue(100)
            self.bar.setFormat('Concluído')
            self.status.setText(f'MP3 salvo com sucesso: {value.name}')
            self.status.setToolTip(str(value))
            self.folder_button.setEnabled(True)
        else:
            self.bar.setValue(0)
            self.bar.setFormat('Cancelado' if kind == 'cancelled' else 'Falha na conversão')
            self.status.setText('Conversão cancelada.' if kind == 'cancelled' else 'Não foi possível converter o arquivo.')
            if kind == 'error' and not self.closing:
                show_error(self, 'Erro na conversão', value)

    def cancel(self):
        self.cancelled.set()
        self.cancel_button.setEnabled(False)
        self.status.setText('Cancelando…')

    def open_folder(self):
        if self.output and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output.parent))):
            show_error(self, 'Não foi possível abrir a pasta', str(self.output.parent))

    def closeEvent(self, event):
        if self.working or (self.worker and self.worker.is_alive()):
            event.ignore()
            if not self.closing and self.close_dialog is None:
                dialog = self.close_dialog = QMessageBox(
                    QMessageBox.Icon.Question, APP_NAME, 'Cancelar a conversão e fechar?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
                dialog.button(QMessageBox.StandardButton.Yes).setText('Sim')
                dialog.button(QMessageBox.StandardButton.No).setText('Não')
                dialog.setDefaultButton(QMessageBox.StandardButton.No)
                dialog.finished.connect(self._close_response)
                dialog.open()
            return
        if self.close_dialog:
            self.close_dialog.reject()
        if self.chooser:
            self.chooser.reject()
        self.timer.stop()
        event.accept()

    def _close_response(self, response):
        self.close_dialog.deleteLater()
        self.close_dialog = None
        if response == QMessageBox.StandardButton.Yes:
            self.closing = True
            self.cancel()
            self.setEnabled(False)


def main():
    # Usado pelo CI para testar o executável completo, sem Python ou FFmpeg no PATH.
    if len(sys.argv) > 1 and sys.argv[1] == '--smoke-test':
        from smoke_test import run
        return run(Path(sys.argv[2]))
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setApplicationVersion(VERSION)
    application.setOrganizationDomain('beecoders.net')
    application.setDesktopFileName(APP_ID)
    window = ConverterWindow()
    window.show()
    return application.exec()


if __name__ == '__main__':
    sys.exit(main())
