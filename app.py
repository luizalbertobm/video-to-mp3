#!/usr/bin/env python3
"""Conversor de WebM e MP4 para MP3 integrado ao desktop GTK do Linux."""

import os
import queue
import sys
import threading
from pathlib import Path

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk

from converter import SOURCE_EXTENSIONS, ConversionCancelled, convert
from dialogs import file_chooser, show_error
from ui import build_window


class ConverterWindow(Gtk.ApplicationWindow):
    def __init__(self, application=None):
        super().__init__(application=application)
        self.source = None
        self.destination = None
        self.output = None
        self.worker = None
        self.cancelled = threading.Event()
        self.events = queue.Queue()
        self.closing = False
        self.working = False
        self.pulsing = False
        self.chooser = None
        self.close_dialog = None
        build_window(self)
        self.connect('delete-event', self.request_close)
        self.connect('destroy', self._destroyed)
        self.poll_id = GLib.timeout_add(100, self._poll)

    def choose_source(self, *_):
        self._choose(False)

    def choose_destination(self, *_):
        self._choose(True)

    def _choose(self, save):
        if self.chooser or self.working:
            return
        self.chooser = file_chooser(self, save=save)
        current = self.destination if save else self.source
        if current:
            self.chooser.set_current_folder(str(current.parent))
            if save:
                self.chooser.set_current_name(current.name)
        elif save:
            self.chooser.set_current_name('reuniao.mp3')
        self.chooser.connect('response', self._file_selected, save)
        self.chooser.show()

    def _file_selected(self, dialog, response, save):
        selected = dialog.get_filename() if response == Gtk.ResponseType.ACCEPT else None
        dialog.destroy()
        self.chooser = None
        if not selected:
            return
        if save:
            target = Path(selected)
            if target.suffix.lower() != '.mp3':
                target = Path(str(target) + '.mp3')
            if os.path.lexists(target):
                show_error(self, 'Esse arquivo já existe', 'Escolha outro nome. Arquivos existentes não são sobrescritos.')
                return
            self.destination = target
            self.destination_row.set_path(target)
            self._reset_result()
        else:
            self.select_source(Path(selected))

    def select_source(self, source):
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
        self.folder_button.set_sensitive(False)
        self.bar.set_fraction(0)
        self.bar.set_text('Pronto para converter')
        self.status.set_text('Confira o destino e clique em Converter para MP3.')

    def _busy(self, busy):
        self.working = busy
        self.source_row.button.set_sensitive(not busy)
        self.destination_row.button.set_sensitive(not busy and self.source is not None)
        self.quality.set_sensitive(not busy)
        self.start_button.set_sensitive(not busy and self.source is not None)
        self.cancel_button.set_sensitive(busy)

    def start(self, *_):
        if self.working or not self.source or not self.destination:
            return
        source, destination = self.source, self.destination
        bitrate = int(self.quality.get_active_id())
        self.cancelled.clear()
        self.output = None
        self.folder_button.set_sensitive(False)
        self._busy(True)
        self.pulsing = True
        self.bar.set_fraction(0)
        self.bar.set_text('Analisando…')
        self.status.set_text('Analisando a gravação…')

        def work():
            try:
                output = convert(source, destination, bitrate, self.cancelled,
                                 lambda value: self.events.put(('progress', value)))
                self.events.put(('done', output))
            except ConversionCancelled:
                self.events.put(('cancelled', None))
            except Exception as error:
                self.events.put(('error', str(error)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'progress':
                    self.status.set_text('Cancelando…' if self.cancelled.is_set() else 'Convertendo o áudio…')
                    self.pulsing = value is None
                    self.bar.set_text('Convertendo…' if value is None else f'{value:.0f}%')
                    if value is not None:
                        self.bar.set_fraction(value / 100)
                else:
                    self._finish(kind, value)
        except queue.Empty:
            pass
        if self.pulsing:
            self.bar.pulse()
        if self.closing and not (self.worker and self.worker.is_alive()):
            self.poll_id = None
            self.destroy()
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _finish(self, kind, value):
        self.pulsing = False
        self._busy(False)
        if kind == 'done':
            self.output = value
            self.bar.set_fraction(1)
            self.bar.set_text('Concluído')
            self.status.set_text(f'MP3 salvo com sucesso: {value.name}')
            self.status.set_tooltip_text(str(value))
            self.folder_button.set_sensitive(True)
        else:
            self.bar.set_fraction(0)
            self.bar.set_text('Cancelado' if kind == 'cancelled' else 'Falha na conversão')
            self.status.set_text('Conversão cancelada.' if kind == 'cancelled' else 'Não foi possível converter o arquivo.')
            if kind == 'error' and not self.closing:
                show_error(self, 'Erro na conversão', value)

    def cancel(self, *_):
        self.cancelled.set()
        self.cancel_button.set_sensitive(False)
        self.status.set_text('Cancelando…')

    def open_folder(self, *_):
        if self.output:
            try:
                Gio.AppInfo.launch_default_for_uri(self.output.parent.as_uri(), None)
            except GLib.Error as error:
                show_error(self, 'Não foi possível abrir a pasta', str(error))

    def request_close(self, *_):
        if not self.working:
            return False
        if not self.close_dialog:
            self.close_dialog = Gtk.MessageDialog(
                transient_for=self, modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO,
                text='Cancelar a conversão e fechar?',
            )
            self.close_dialog.set_default_response(Gtk.ResponseType.NO)
            self.close_dialog.connect('response', self._close_response)
            self.close_dialog.show()
        return True

    def _close_response(self, dialog, response):
        dialog.destroy()
        self.close_dialog = None
        if response == Gtk.ResponseType.YES:
            self.closing = True
            self.cancel()
            self.set_sensitive(False)

    def _destroyed(self, *_):
        if self.poll_id:
            GLib.source_remove(self.poll_id)
            self.poll_id = None
        if self.chooser:
            self.chooser.destroy()
            self.chooser = None


class ConverterApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='net.beecoders.WebmToMp3')

    def do_activate(self):
        window = self.get_active_window()
        if window is None:
            window = ConverterWindow(self)
        window.show_all()
        window.present()


if __name__ == '__main__':
    GLib.set_prgname('webm-to-mp3')
    GLib.set_application_name('Vídeo para MP3')
    sys.exit(ConverterApplication().run(sys.argv))
