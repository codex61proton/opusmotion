#!/usr/bin/env bash
set -e
cd /tmp/hoplite/workspace
/opt/spy/.venv/bin/python tools/rerender_end.py
tools/assemble.sh
tools/mux.sh build/render/master_video.mp4 build/audio/mix.wav deliverables/the_moon_files.mp4
echo ALLDONE
