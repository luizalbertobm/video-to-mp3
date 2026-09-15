"""Qt Widgets com estilo, paleta e controles de janela do sistema."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)
from runtime import APP_NAME, resource_path

QUALITY_OPTIONS = ((64, '64 kbps — Arquivo menor'), (128, '128 kbps — Equilibrado'),
                   (192, '192 kbps — Alta qualidade'), (320, '320 kbps — Qualidade máxima'))


def label(text):
    widget = QLabel(text)
    widget.setWordWrap(True)
    return widget


class FileRow(QFrame):
    def __init__(self, title, hint, action, callback):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        content = QVBoxLayout()
        self.title = label(title)
        self.path = label(hint)
        self.path.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        content.addWidget(self.title)
        content.addWidget(self.path)
        layout.addLayout(content, 1)
        self.button = QPushButton(action)
        self.button.clicked.connect(callback)
        layout.addWidget(self.button)

    def set_path(self, path):
        self.title.setText(path.name)
        self.path.setText(str(path.parent))
        self.setToolTip(str(path))


def build_window(window):
    window.setWindowTitle(APP_NAME)
    window.setWindowIcon(QIcon(str(resource_path('assets/icon.png'))))
    window.resize(660, 570)
    window.setMinimumWidth(500)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    window.setCentralWidget(scroll)
    panel = QWidget()
    scroll.setWidget(panel)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(18)
    intro = label('Converta suas gravações em áudio')
    font = intro.font()
    font.setPointSizeF(font.pointSizeF() * 1.3)
    font.setBold(True)
    intro.setFont(font)
    layout.addWidget(intro)
    window.source_row = FileRow('Gravação WebM ou MP4', 'Selecione o arquivo que deseja converter',
                                '&Selecionar…', window.choose_source)
    window.destination_row = FileRow('Destino do MP3', 'Escolha primeiro uma gravação',
                                     'Salvar co&mo…', window.choose_destination)
    window.destination_row.button.setEnabled(False)
    layout.addWidget(window.source_row)
    layout.addWidget(window.destination_row)
    quality_row = QHBoxLayout()
    quality_label = QLabel('&Qualidade do áudio')
    window.quality = QComboBox()
    window.quality.setAccessibleName('Qualidade do áudio')
    for bitrate, title in QUALITY_OPTIONS:
        window.quality.addItem(title, bitrate)
    window.quality.setCurrentIndex(1)
    quality_label.setBuddy(window.quality)
    quality_row.addWidget(quality_label, 1)
    quality_row.addWidget(window.quality)
    layout.addLayout(quality_row)
    layout.addWidget(label('128 kbps é uma boa opção para reuniões e transcrições.'))
    window.bar = QProgressBar()
    window.bar.setAccessibleName('Progresso da conversão')
    window.bar.setRange(0, 100)
    window.bar.setValue(0)
    window.bar.setFormat('Aguardando arquivo')
    layout.addWidget(window.bar)
    window.status = label('Selecione uma gravação para começar.')
    window.status.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(window.status)
    buttons = QHBoxLayout()
    window.start_button = QPushButton('&Converter para MP3')
    window.start_button.setEnabled(False)
    window.start_button.clicked.connect(window.start)
    window.cancel_button = QPushButton('C&ancelar')
    window.cancel_button.setEnabled(False)
    window.cancel_button.clicked.connect(window.cancel)
    window.folder_button = QPushButton('Abrir &pasta')
    window.folder_button.setEnabled(False)
    window.folder_button.clicked.connect(window.open_folder)
    for button in (window.start_button, window.cancel_button, window.folder_button):
        buttons.addWidget(button)
    layout.addLayout(buttons)
    layout.addStretch()
    layout.addWidget(label('Conversão local. O arquivo original é preservado.'))
