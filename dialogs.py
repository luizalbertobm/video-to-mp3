"""Seletores nativos e mensagens Qt."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox


def file_chooser(parent, *, save=False):
    dialog = QFileDialog(parent, 'Salvar áudio MP3' if save else 'Selecionar gravação WebM ou MP4')
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave if save else QFileDialog.AcceptMode.AcceptOpen)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile if save else QFileDialog.FileMode.ExistingFile)
    dialog.setNameFilter('Áudio MP3 (*.mp3 *.MP3)' if save else
                         'Gravação WebM ou MP4 (*.webm *.WEBM *.mp4 *.MP4)')
    dialog.setLabelText(QFileDialog.DialogLabel.Accept, 'Salvar' if save else 'Abrir')
    dialog.setLabelText(QFileDialog.DialogLabel.Reject, 'Cancelar')
    dialog.setSupportedSchemes(['file'])
    dialog.setModal(True)
    if save:
        dialog.setDefaultSuffix('mp3')
        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, True)
    return dialog


def show_error(parent, title, detail):
    dialog = QMessageBox(QMessageBox.Icon.Critical, title, title,
                         QMessageBox.StandardButton.Close, parent)
    dialog.button(QMessageBox.StandardButton.Close).setText('Fechar')
    dialog.setTextFormat(Qt.TextFormat.PlainText)
    dialog.setInformativeText(detail)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dialog.open()
    return dialog
