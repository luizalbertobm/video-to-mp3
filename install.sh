#!/usr/bin/env bash
# Integração opcional do pacote Linux ou checkout ao menu do usuário.
set -euo pipefail
app_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
applications="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
entry="$applications/net.beecoders.WebmToMp3.desktop"
refresh_menu() {
    if command -v update-desktop-database >/dev/null; then
        update-desktop-database "$applications" 2>/dev/null || true
    fi
}
if [[ ${1-} == --uninstall && $# == 1 ]]; then
    rm -f -- "$entry"
    refresh_menu
    echo 'Lançador removido. A aplicação e os arquivos de áudio foram preservados.'
    exit 0
fi
if [[ ${1-} == --help || ${1-} == -h ]]; then
    echo 'Uso: ./install.sh [--uninstall]'
    exit 0
fi
[[ $# == 0 ]] || { echo 'Use ./install.sh [--uninstall]' >&2; exit 2; }
# Escapes do campo Exec: primeiro a camada de aspas, depois a do arquivo desktop.
quote_exec() {
    local value=$1
    value=${value//\\/\\\\}
    value=${value//\"/\\\"}
    value=${value//\$/\\\$}
    value=${value//\`/\\\`}
    value=${value//%/%%}
    value=${value//\\/\\\\}
    printf '"%s"' "$value"
}
# O WM_CLASS vem do nome do executável: video-to-mp3 no pacote, app.py no fonte.
if [[ -x "$app_dir/video-to-mp3" ]]; then
    executable=$(quote_exec "$app_dir/video-to-mp3")
    wmclass='video-to-mp3'
else
    wmclass='app.py'
    interpreter="$app_dir/.venv/bin/python"
    [[ -x "$interpreter" ]] || interpreter=$(command -v python3)
    "$interpreter" -c 'import PySide6' || { echo 'Instale as dependências conforme o README.' >&2; exit 1; }
    # O lançador roda sem terminal: um Qt que não inicia falharia em silêncio
    # absoluto ao clicar no menu, sem janela e sem mensagem de erro.
    if [[ -n "${WAYLAND_DISPLAY-}${DISPLAY-}" ]] \
        && ! "$interpreter" -c 'from PySide6.QtGui import QGuiApplication; QGuiApplication([])' 2>/dev/null; then
        echo 'Aviso: o Qt não conseguiu abrir uma janela nesta sessão.' >&2
        echo 'Em Ubuntu/Zorin, as bibliotecas de desktop costumam resolver:' >&2
        echo '  sudo apt install libgl1 libegl1 libopengl0 libxcb-cursor0 libxkbcommon-x11-0' >&2
        echo 'O lançador será criado mesmo assim.' >&2
    fi
    executable="$(quote_exec "$interpreter") $(quote_exec "$app_dir/app.py")"
fi
icon="$app_dir/assets/icon.png"
icon=${icon//\\/\\\\}
template=$(<"$app_dir/video-to-mp3.desktop.in")
template=${template//__EXEC__/$executable}
template=${template//__ICON__/$icon}
template=${template//__WMCLASS__/$wmclass}
mkdir -p "$applications"
printf '%s\n' "$template" > "$entry"
chmod 644 "$entry"
if command -v desktop-file-validate >/dev/null; then
    desktop-file-validate "$entry"
fi
for previous in video-to-mp3.desktop webm-to-mp3.desktop; do
    old="$applications/$previous"
    if [[ -f "$old" ]] && grep -Fq -- "$app_dir" "$old"; then
        rm -f -- "$old"
    fi
done
refresh_menu
echo "Lançador instalado: $entry"
echo 'Mantenha a pasta da aplicação neste local enquanto usar o lançador.'
