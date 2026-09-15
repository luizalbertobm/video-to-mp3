"""Conversão local com FFmpeg, progresso e publicação sem sobrescrita."""
import errno
import json
import math
import os
import queue
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

from runtime import find_tool, spawn, stop_process

SOURCE_EXTENSIONS = (".webm", ".mp4")


class ConversionError(Exception):
    pass


class ConversionCancelled(Exception):
    pass


def _check_cancelled(cancelled):
    if cancelled.is_set():
        raise ConversionCancelled()


def _capture(arguments, cancelled, timeout=20):
    """Drena ambos os pipes enquanto permite cancelar inclusive o FFprobe."""
    _check_cancelled(cancelled)
    process = spawn(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace")
    deadline = time.monotonic() + timeout
    try:
        while True:
            _check_cancelled(cancelled)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ConversionError("A ferramenta demorou demais para analisar o arquivo.")
            try:
                output, errors = process.communicate(timeout=min(0.1, remaining))
                _check_cancelled(cancelled)
                return process.returncode, output, errors
            except subprocess.TimeoutExpired:
                continue
    finally:
        stop_process(process)
        process.communicate()
        process.stdout.close()
        process.stderr.close()


def _publish(temporary, destination, cancelled):
    _check_cancelled(cancelled)
    try:
        os.link(temporary, destination)
        return
    except OSError as error:
        # Não mascarar falta de espaço, destino ocupado ou outros erros reais.
        unsupported = {errno.EXDEV, errno.EPERM, errno.ENOSYS, errno.EOPNOTSUPP,
                       getattr(errno, "ENOTSUP", errno.EOPNOTSUPP)}
        if error.errno not in unsupported and getattr(error, "winerror", None) not in (1, 17, 50):
            raise
    # FAT/exFAT não suportam hard links. A abertura exclusiva mantém a garantia
    # de nunca sobrescrever; a cópia fica visível até concluir.
    with temporary.open("rb") as source:
        output = destination.open("xb")
        identity = os.fstat(output.fileno())
        try:
            with output:
                while True:
                    _check_cancelled(cancelled)
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                output.flush()
                _check_cancelled(cancelled)
        except BaseException:
            # Não remover um arquivo que outra aplicação colocou no lugar.
            try:
                if os.path.samestat(identity, destination.stat(follow_symlinks=False)):
                    destination.unlink()
            except FileNotFoundError:
                pass
            raise


def convert(source: Path, destination: Path, bitrate: int,
            cancelled: threading.Event,
            progress: Callable[[float | None], None]) -> Path:
    try:
        return _convert(source, destination, bitrate, cancelled, progress)
    except FileExistsError as error:
        raise ConversionError("O destino já existe. Escolha outro nome para salvar.") from error
    except PermissionError as error:
        raise ConversionError("Sem permissão para ler a gravação ou gravar na pasta de destino.") from error
    except OSError as error:
        if error.errno == errno.ENOSPC:
            raise ConversionError("Não há espaço suficiente na pasta de destino.") from error
        raise ConversionError(f"Não foi possível acessar os arquivos ou executar FFmpeg: {error}") from error


def _convert(source, destination, bitrate, cancelled, progress):
    source, destination = source.expanduser().resolve(), destination.expanduser().absolute()
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
    _check_cancelled(cancelled)
    try:
        ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
    except FileNotFoundError as error:
        raise ConversionError(str(error)) from error
    code, encoders, _ = _capture([ffmpeg, "-hide_banner", "-encoders"], cancelled)
    if code or not any(len(parts := line.split()) > 1 and parts[1] == "libmp3lame"
                       for line in encoders.splitlines()):
        raise ConversionError("Este FFmpeg não possui o encoder libmp3lame necessário para gerar MP3.")
    code, output, _ = _capture(
        [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,duration",
         "-of", "json", source], cancelled)
    try:
        metadata = json.loads(output) if code == 0 else {}
    except ValueError as error:
        raise ConversionError("Não foi possível analisar o arquivo de vídeo.") from error
    if not isinstance(metadata, dict) or not any(
        isinstance(stream, dict) and stream.get("codec_type") == "audio"
        for stream in metadata.get("streams", [])
    ):
        raise ConversionError("O arquivo está inválido ou não contém uma faixa de áudio.")
    try:
        duration = float(metadata.get("format", {}).get("duration", 0))
        if not math.isfinite(duration):
            duration = 0
    except (ValueError, TypeError):
        duration = 0
    _check_cancelled(cancelled)
    progress(0 if duration > 0 else None)
    temporary = process = reader = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".video-to-mp3-", suffix=".mp3", dir=destination.parent)
        os.close(descriptor)
        temporary = Path(name)
        with tempfile.TemporaryFile() as errors:
            process = spawn(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                 "-i", source, "-map", "0:a:0", "-vn", "-c:a", "libmp3lame",
                 "-b:a", f"{bitrate}k", "-ac", "2", "-ar", "44100",
                 "-progress", "pipe:1", "-nostats", temporary],
                stdout=subprocess.PIPE, stderr=errors, text=True, encoding="utf-8", errors="replace")
            updates = queue.Queue()

            def read_progress():
                try:
                    for line in process.stdout:
                        updates.put(line)
                finally:
                    updates.put(None)

            reader = threading.Thread(target=read_progress, daemon=True)
            reader.start()
            ended = False
            while not ended or process.poll() is None:
                _check_cancelled(cancelled)
                try:
                    line = updates.get(timeout=0.1)
                except queue.Empty:
                    continue
                if line is None:
                    ended = True
                    continue
                key, _, value = line.strip().partition("=")
                if key == "out_time_us" and duration > 0:
                    try:
                        progress(min(99.0, max(0.0, float(value) / 10000 / duration)))
                    except ValueError:
                        pass
            _check_cancelled(cancelled)
            if process.returncode != 0:
                errors.seek(0, os.SEEK_END)
                errors.seek(max(0, errors.tell() - 2000))
                detail = errors.read().decode("utf-8", errors="replace").strip()
                raise ConversionError(f"O FFmpeg não conseguiu converter o arquivo.\n\n{detail}")
            if not temporary.stat().st_size:
                raise ConversionError("O FFmpeg gerou um arquivo vazio.")
            _publish(temporary, destination, cancelled)
            progress(100.0)
            return destination
    finally:
        if process is not None:
            stop_process(process)
            if reader is not None:
                reader.join()
            process.stdout.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)
