#!/usr/bin/env bash
# Instala (ou remove) o lançador de menu do Vídeo para MP3 para o usuário atual.
# A aplicação roda direto desta pasta; nada é copiado para fora dela.

set -euo pipefail

app_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
template="$app_dir/video-to-mp3.desktop.in"
applications="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
entry="$applications/video-to-mp3.desktop"
# Versões anteriores do projeto instalavam o lançador com este nome.
legacy="$applications/webm-to-mp3.desktop"

refresh_menu() {
    if command -v update-desktop-database >/dev/null; then
        update-desktop-database "$applications" 2>/dev/null || true
    fi
}

if [[ ${1-} == --uninstall ]]; then
    rm -f -- "$entry"
    refresh_menu
    echo "Lançador removido: $entry"
    echo "A pasta da aplicação foi preservada."
    exit 0
fi

if [[ ${1-} == --help || ${1-} == -h ]]; then
    echo "Uso: ./install.sh [--uninstall]"
    echo
    echo "Sem argumentos, cria o lançador de menu apontando para esta pasta."
    echo "Com --uninstall, remove o lançador e preserva a aplicação."
    exit 0
fi

if [[ $# -gt 0 ]]; then
    echo "Argumento desconhecido: $1" >&2
    echo "Use ./install.sh --help" >&2
    exit 2
fi

[[ -f "$app_dir/app.py" ]] || { echo "app.py não encontrado em $app_dir" >&2; exit 1; }
[[ -f "$template" ]] || { echo "Template não encontrado: $template" >&2; exit 1; }

missing=()
command -v python3 >/dev/null || missing+=("python3")
command -v ffmpeg  >/dev/null || missing+=("ffmpeg")
command -v ffprobe >/dev/null || missing+=("ffmpeg (ffprobe)")
python3 -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null \
    || missing+=("python3-gi e gir1.2-gtk-3.0")
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Aviso: faltam requisitos para executar a aplicação:" >&2
    printf '  - %s\n' "${missing[@]}" >&2
    echo "Em Debian/Ubuntu: sudo apt install python3 python3-gi gir1.2-gtk-3.0 ffmpeg" >&2
    echo "O lançador será criado mesmo assim." >&2
fi

mkdir -p -- "$applications"
# A substituição é feita pelo bash, e não por sed, para que caminhos com
# espaços, acentos ou barras invertidas cheguem intactos ao lançador.
template_text=$(<"$template")
printf '%s\n' "${template_text//__APP_DIR__/$app_dir}" > "$entry"
chmod 644 -- "$entry"

if command -v desktop-file-validate >/dev/null; then
    desktop-file-validate "$entry" || {
        echo "O lançador gerado é inválido; nada foi instalado." >&2
        rm -f -- "$entry"
        exit 1
    }
fi

if [[ -f "$legacy" ]] && grep -q 'webm-to-mp3' -- "$legacy" && grep -q 'app\.py' -- "$legacy"; then
    rm -f -- "$legacy"
    echo "Lançador antigo removido: $legacy"
fi

refresh_menu

echo "Lançador instalado: $entry"
echo "Aponta para: $app_dir"
echo "Procure por \"Vídeo para MP3\" no menu de aplicativos."
