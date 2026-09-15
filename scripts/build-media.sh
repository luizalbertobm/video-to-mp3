#!/usr/bin/env bash
# Native Linux/macOS or MSYS2 MINGW64. No system FFmpeg is copied into a release.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work="$root/build/media"
prefix="$work/prefix"
sources="$root/build/sources"
mkdir -p "$work" "$sources" "$root/vendor/bin" "$root/vendor/licenses" "$root/vendor/sources"
fetch() {
    local url=$1 name=$2 expected=$3 actual
    if [[ ! -f "$sources/$name" ]]; then
        curl -fL --retry 3 "$url" -o "$sources/$name"
    fi
    actual=$(shasum -a 256 "$sources/$name" | cut -d ' ' -f 1)
    [[ "$actual" == "$expected" ]] || { echo "Invalid SHA256: $name" >&2; exit 1; }
    cp "$sources/$name" "$root/vendor/sources/"
}
fetch https://ffmpeg.org/releases/ffmpeg-8.1.1.tar.xz ffmpeg-8.1.1.tar.xz b6863adde98898f42602017462871b5f6333e65aec803fdd7a6308639c52edf3
fetch https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz lame-3.100.tar.gz ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e
tar -xf "$sources/lame-3.100.tar.gz" -C "$work"
tar -xf "$sources/ffmpeg-8.1.1.tar.xz" -C "$work"
export CFLAGS="${CFLAGS:-} -O2"
if [[ $(uname -s) == Darwin ]]; then
    export MACOSX_DEPLOYMENT_TARGET=13.0
    export CFLAGS="$CFLAGS -mmacosx-version-min=13.0"
    export LDFLAGS="${LDFLAGS:-} -mmacosx-version-min=13.0"
fi
jobs=${BUILD_JOBS:-4}
cd "$work/lame-3.100"
./configure --prefix="$prefix" --disable-shared --enable-static --disable-frontend --disable-nasm
make -j"$jobs"
make install
cd "$work/ffmpeg-8.1.1"
extra=()
case $(uname -s) in
    MINGW*|MSYS*) extra+=(--target-os=mingw32 --extra-ldflags=-static) ;;
esac
./configure --prefix="$prefix" --disable-autodetect --disable-network --disable-doc \
    --disable-debug --disable-shared --enable-static --disable-x86asm \
    --disable-everything --enable-ffmpeg --enable-ffprobe --disable-ffplay \
    --enable-protocol=file,pipe --enable-demuxer=matroska,mov,wav,mp3 \
    --enable-decoder=aac,aac_fixed,aac_latm,opus,vorbis,mp3,mp3float,pcm_s16le,alac,flac \
    --enable-parser=aac,aac_latm,opus,vorbis,mpegaudio,flac \
    --enable-muxer=mp3,mp4,webm --enable-encoder=libmp3lame,aac,vorbis \
    --enable-filter=aresample,aformat,anull,sine --enable-indev=lavfi \
    --enable-libmp3lame --extra-cflags="-I$prefix/include $CFLAGS" \
    --extra-ldflags="-L$prefix/lib ${LDFLAGS:-}" "${extra[@]}"
make -j"$jobs"
make install
extension=""
case $(uname -s) in MINGW*|MSYS*) extension=.exe ;; esac
for tool in ffmpeg ffprobe; do
    cp "$prefix/bin/$tool$extension" "$root/vendor/bin/"
done
cp COPYING.LGPLv2.1 "$root/vendor/licenses/FFmpeg-LGPL-2.1.txt"
cp "$work/lame-3.100/COPYING" "$root/vendor/licenses/LAME-LGPL-2.0.txt"
cp "$root/scripts/build-media.sh" "$root/vendor/sources/"
cp ffbuild/config.log "$root/vendor/sources/ffmpeg-config.log"
"$root/vendor/bin/ffmpeg$extension" -version > "$root/vendor/ffmpeg-build.txt"
(cd "$root/vendor" && shasum -a 256 bin/* sources/*.tar.* > SHA256SUMS)
echo 'Media tools ready in vendor/'
