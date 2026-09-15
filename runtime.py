"""Localização de recursos e execução de ferramentas em todos os sistemas."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

APP_NAME = "Vídeo para MP3"
APP_ID = "net.beecoders.WebmToMp3"
VERSION = "1.0.0"


def resource_path(name: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def find_tool(name: str) -> Path:
    if getattr(sys, "frozen", False):
        executable = resource_path("bin") / (name + (".exe" if os.name == "nt" else ""))
        if executable.is_file():
            return executable.resolve()
        raise FileNotFoundError(f"{name} não foi incluído no aplicativo. Baixe novamente o pacote completo.")
    executable = shutil.which(name)
    if executable:
        return Path(executable).resolve()
    raise FileNotFoundError(f"{name} não encontrado. Instale FFmpeg e FFprobe e adicione-os ao PATH.")


def spawn(arguments, **kwargs):
    # Qt e os subprocessos nunca precisam de um shell ou de uma janela de console.
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen([str(arg) for arg in arguments], **kwargs)


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
