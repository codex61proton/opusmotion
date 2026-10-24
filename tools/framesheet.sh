#!/usr/bin/env bash
# framesheet.sh VIDEO OUTDIR t1 t2 ... — extract frames at times (s) and tile them 6-up at 1/3 scale
set -euo pipefail
V="$1"; D="$2"; shift 2; mkdir -p "$D"; rm -f "$D"/f_*.png
i=0; for t in "$@"; do ffmpeg -v error -y -ss "$t" -i "$V" -frames:v 1 -vf scale=360:640 "$D/f_$(printf %03d $i).png"; i=$((i+1)); done
ffmpeg -v error -y -pattern_type glob -i "$D/f_*.png" -vf "tile=6x$(( (i+5)/6 )):padding=4:color=white" -frames:v 1 "$D/sheet.jpg"
echo "$D/sheet.jpg"
