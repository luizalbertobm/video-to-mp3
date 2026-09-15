#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
docker build -t video-to-mp3-smoke-base -f "$root/scripts/Dockerfile.smoke" "$root/scripts"
docker run --rm --network none \
    --mount "type=bind,source=$root/dist,target=/packages,readonly" \
    video-to-mp3-smoke-base /bin/sh -c '
        set -eu
        ! command -v python3
        ! command -v ffmpeg
        mkdir /app
        tar -xzf /packages/video-to-mp3-*-linux-x64.tar.gz -C /app
        cd /tmp
        executable=$(find /app -maxdepth 2 -name video-to-mp3 -type f)
        PATH="" "$executable" --smoke-test /tmp/results
        cat /tmp/results/smoke-result.json
    '
