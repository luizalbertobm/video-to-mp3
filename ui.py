"""Componentes GTK que herdam o tema, as fontes e os ícones do sistema."""

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango


QUALITY_OPTIONS = (
    (64, '64 kbps — Arquivo menor'),
    (128, '128 kbps — Equilibrado'),
    (192, '192 kbps — Alta qualidade'),
    (320, '320 kbps — Qualidade máxima'),
)


def label(text, *, dim=False):
    widget = Gtk.Label(label=text, xalign=0)
    widget.set_line_wrap(True)
    widget.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    if dim:
        widget.get_style_context().add_class('dim-label')
    return widget


class FileRow(Gtk.Frame):
    def __init__(self, title, hint, icon, action, callback):
        super().__init__()
        self.set_shadow_type(Gtk.ShadowType.IN)
        box = Gtk.Box(spacing=16, margin=16)
        self.add(box)
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DND)
        box.pack_start(image, False, False, 0)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        content.set_hexpand(True)
        box.pack_start(content, True, True, 0)
        self.title = Gtk.Label(label=title, xalign=0)
        self.title.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        content.pack_start(self.title, False, False, 0)
        self.path = Gtk.Label(label=hint, xalign=0)
        self.path.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.path.set_max_width_chars(45)
        self.path.get_style_context().add_class('dim-label')
        content.pack_start(self.path, False, False, 0)
        self.button = Gtk.Button.new_with_mnemonic(action)
        self.button.set_valign(Gtk.Align.CENTER)
        self.button.connect('clicked', callback)
        box.pack_end(self.button, False, False, 0)

    def set_path(self, path):
        self.title.set_text(path.name)
        self.path.set_text(str(path.parent))
        self.set_tooltip_text(str(path))


def build_window(window):
    window.set_title('Vídeo para MP3')
    window.set_icon_name('audio-x-generic')
    window.set_default_size(660, 570)
    window.set_size_request(560, -1)
    header = Gtk.HeaderBar(title='Vídeo para MP3', show_close_button=True)
    window.set_titlebar(header)
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    window.add(scroll)
    panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin=24)
    scroll.add(panel)
    intro = label('Converta suas gravações em áudio')
    intro.get_style_context().add_class('title')
    panel.pack_start(intro, False, False, 0)
    window.source_row = FileRow('Gravação WebM ou MP4', 'Selecione o arquivo que deseja converter',
                                'video-x-generic', '_Selecionar…', window.choose_source)
    panel.pack_start(window.source_row, False, False, 0)
    window.destination_row = FileRow('Destino do MP3', 'Escolha primeiro uma gravação',
                                     'audio-x-generic', 'Salvar _como…', window.choose_destination)
    window.destination_row.button.set_sensitive(False)
    panel.pack_start(window.destination_row, False, False, 0)
    quality_row = Gtk.Box(spacing=18)
    quality_label = Gtk.Label.new_with_mnemonic('_Qualidade do áudio')
    quality_label.set_xalign(0)
    quality_row.pack_start(quality_label, True, True, 0)
    window.quality = Gtk.ComboBoxText()
    for bitrate, title in QUALITY_OPTIONS:
        window.quality.append(str(bitrate), title)
    window.quality.set_active_id('128')
    quality_label.set_mnemonic_widget(window.quality)
    quality_row.pack_end(window.quality, False, False, 0)
    panel.pack_start(quality_row, False, False, 0)
    panel.pack_start(label('128 kbps é uma boa opção para reuniões e transcrições.', dim=True), False, False, 0)
    progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    window.bar = Gtk.ProgressBar(show_text=True)
    window.bar.set_text('Aguardando arquivo')
    window.bar.get_accessible().set_name('Progresso da conversão')
    progress_box.pack_start(window.bar, False, False, 0)
    window.status = label('Selecione uma gravação para começar.', dim=True)
    progress_box.pack_start(window.status, False, False, 0)
    panel.pack_start(progress_box, False, False, 0)
    buttons = Gtk.Box(spacing=10)
    window.start_button = Gtk.Button.new_with_mnemonic('_Converter para MP3')
    window.start_button.get_style_context().add_class('suggested-action')
    window.start_button.set_sensitive(False)
    window.start_button.connect('clicked', window.start)
    buttons.pack_start(window.start_button, False, False, 0)
    window.cancel_button = Gtk.Button.new_with_mnemonic('C_ancelar')
    window.cancel_button.set_sensitive(False)
    window.cancel_button.connect('clicked', window.cancel)
    buttons.pack_start(window.cancel_button, False, False, 0)
    window.folder_button = Gtk.Button.new_with_mnemonic('Abrir _pasta')
    window.folder_button.set_sensitive(False)
    window.folder_button.connect('clicked', window.open_folder)
    buttons.pack_end(window.folder_button, False, False, 0)
    panel.pack_start(buttons, False, False, 0)
    panel.pack_start(Gtk.Separator(), False, False, 0)
    panel.pack_start(label('Conversão local. O arquivo original é preservado.', dim=True), False, False, 0)
