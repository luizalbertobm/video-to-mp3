"""Conversão local com FFmpeg, progresso e publicação sem sobrescrita."""

import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Callable


# Formatos de entrada aceitos; o áudio de qualquer um deles vira MP3.
SOURCE_EXTENSIONS = (".webm", ".mp4")


class ConversionError(Exception):
    pass


class ConversionCancelled(Exception):
    pass


def convert(source: Path, destination: Path, bitrate: int,
            cancelled: threading.Event,
            progress: Callable[[float | None], None]) -> Path:
    source, destination = source.expanduser().resolve(), destination.expanduser().absolute()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ConversionError("FFmpeg não encontrado. Instale o pacote ffmpeg da sua distribuição.")
    if not source.is_file() or source.suffix.lower() not in SOURCE_EXTENSIONS:
        raise ConversionError("Selecione um arquivo WebM ou MP4 válido.")
    if destination.suffix.lower() != ".mp3":
        raise ConversionError("O arquivo de saída deve ter a extensão .mp3.")
    if os.path.lexists(destination):
        raise ConversionError("Já existe um arquivo nesse destino. Escolha outro nome.")
    if not destination.parent.is_dir():
        raise ConversionError("A pasta de destino não existe.")
    if bitrate not in (64, 128, 192, 320):
        raise ConversionError("Qualidade de áudio inválida.")
    if cancelled.is_set():
        raise ConversionCancelled()
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,duration",
             "-of", "json", str(source)], capture_output=True, text=True,
            errors="replace", timeout=20, check=False,
        )
        metadata = json.loads(probe.stdout) if probe.returncode == 0 else {}
    except (subprocess.TimeoutExpired, ValueError) as error:
        raise ConversionError("Não foi possível analisar o arquivo de vídeo.") from error
    streams = metadata.get("streams", [])
    if not any(stream.get("codec_type") == "audio" for stream in streams):
        raise ConversionError("O arquivo está inválido ou não contém uma faixa de áudio.")
    try:
        duration = float(metadata.get("format", {}).get("duration", 0))
    except (ValueError, TypeError):
        duration = 0
    if cancelled.is_set():
        raise ConversionCancelled()
    progress(0 if duration > 0 else None)
    temporary = None
    process = None
    reader = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".video-to-mp3-", suffix=".mp3", dir=destination.parent)
        os.close(descriptor)
        temporary = Path(name)
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                 "-i", str(source), "-map", "0:a:0", "-vn", "-c:a", "libmp3lame",
                 "-b:a", f"{bitrate}k", "-ac", "2", "-ar", "44100",
                 "-progress", "pipe:1", "-nostats", str(temporary)],
                stdout=subprocess.PIPE, stderr=errors, text=True, errors="replace",
            )
            updates: queue.Queue[str] = queue.Queue()

            def read_progress() -> None:
                if process.stdout is not None:
                    for line in process.stdout:
                        updates.put(line)

            reader = threading.Thread(target=read_progress, daemon=True)
            reader.start()
            while process.poll() is None or not updates.empty():
                if cancelled.is_set():
                    raise ConversionCancelled()
                try:
                    line = updates.get(timeout=0.1)
                except queue.Empty:
                    continue
                key, _, value = line.strip().partition("=")
                if key == "out_time_us" and duration > 0:
                    try:
                        progress(min(99.0, max(0.0, float(value) / 10000 / duration)))
                    except ValueError:
                        pass
            if cancelled.is_set():
                raise ConversionCancelled()
            if process.returncode != 0:
                errors.seek(0, os.SEEK_END)
                errors.seek(max(0, errors.tell() - 2000))
                detail = errors.read().decode("utf-8", errors="replace").strip()
                raise ConversionError(f"O FFmpeg não conseguiu converter o arquivo.\n\n{detail}")
            if not temporary.stat().st_size:
                raise ConversionError("O FFmpeg gerou um arquivo vazio.")
            # A criacao do link e atomica e falha caso outro arquivo ocupe o destino.
            os.link(temporary, destination)
            progress(100.0)
            return destination
    except FileExistsError as error:
        raise ConversionError("O destino já existe. Escolha outro nome para salvar.") from error
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if reader is not None:
                reader.join(timeout=2)
            if process.stdout is not None:
                process.stdout.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)
