"""Diálogos nativos GTK para abrir, salvar e informar erros."""

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from converter import SOURCE_EXTENSIONS


def file_chooser(parent, *, save=False):
    dialog = Gtk.FileChooserNative.new(
        'Salvar áudio MP3' if save else 'Selecionar gravação WebM ou MP4', parent,
        Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN,
        '_Salvar' if save else '_Abrir', '_Cancelar',
    )
    dialog.set_modal(True)
    dialog.set_local_only(True)
    file_filter = Gtk.FileFilter()
    file_filter.set_name('Áudio MP3' if save else 'Gravação WebM ou MP4')
    if save:
        patterns = ('*.mp3', '*.MP3')
    else:
        patterns = tuple(pattern for suffix in SOURCE_EXTENSIONS
                         for pattern in (f'*{suffix}', f'*{suffix.upper()}'))
    for pattern in patterns:
        file_filter.add_pattern(pattern)
    if not save:
        for mime in ('video/webm', 'audio/webm', 'video/mp4', 'audio/mp4'):
            file_filter.add_mime_type(mime)
    dialog.add_filter(file_filter)
    if save:
        dialog.set_create_folders(True)
        # O conversor nunca sobrescreve arquivos; um destino ocupado recebe um erro.
        dialog.set_do_overwrite_confirmation(False)
    return dialog


def show_error(parent, title, detail):
    dialog = Gtk.MessageDialog(
        transient_for=parent, modal=True, destroy_with_parent=True,
        message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, text=title,
    )
    dialog.format_secondary_text(detail)
    dialog.connect('response', lambda widget, response: widget.destroy())
    dialog.show()
    return dialog
