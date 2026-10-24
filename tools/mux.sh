#!/usr/bin/env bash
# mux.sh VIDEO MIX.wav OUT.mp4 — two-pass EBU R128 normalisation to -14 LUFS / -1 dBTP, AAC 256k
set -euo pipefail
V="$1"; A="$2"; O="$3"
J=$(ffmpeg -hide_banner -nostats -i "$A" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
mi=$(echo "$J" | jq -r .input_i); mtp=$(echo "$J" | jq -r .input_tp); mlra=$(echo "$J" | jq -r .input_lra); mth=$(echo "$J" | jq -r .input_thresh); off=$(echo "$J" | jq -r .target_offset)
ffmpeg -hide_banner -loglevel error -y -i "$V" -i "$A" \
  -filter_complex "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$mi:measured_TP=$mtp:measured_LRA=$mlra:measured_thresh=$mth:offset=$off:linear=true,aresample=48000[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart \
  -metadata title="The Moon Files: two declassified Cold War operations" "$O"
echo "muxed $O"
