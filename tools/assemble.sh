#!/usr/bin/env bash
# Splice the first-pass render with re-rendered ranges (frame-accurate) and encode the master video.
# Frame map: half_a[0,255) r_u2[255,420) half_a[420,810) r_moon[810,885) half_a[885,1308) r_sites_end[1308,3510) r_end[3510,3707)
set -euo pipefail
R=build/render
ffmpeg -hide_banner -loglevel error -y -i $R/half_a.mp4 -i $R/r_u2.mp4 -i $R/r_moon.mp4 -i $R/r_sites_end.mp4 -i $R/r_end.mp4 -filter_complex "
[0:v]split=3[x1][x2][x3];
[x1]trim=start_frame=0:end_frame=255,setpts=PTS-STARTPTS[a];
[1:v]setpts=PTS-STARTPTS[b];
[x2]trim=start_frame=420:end_frame=810,setpts=PTS-STARTPTS[c];
[2:v]setpts=PTS-STARTPTS[d];
[x3]trim=start_frame=885:end_frame=1308,setpts=PTS-STARTPTS[e];
[3:v]trim=start_frame=0:end_frame=2202,setpts=PTS-STARTPTS[f];
[4:v]setpts=PTS-STARTPTS[g];
[a][b][c][d][e][f][g]concat=n=7:v=1:a=0,fps=30,format=yuv420p[v]" -map "[v]" \
  -c:v libx264 -preset medium -crf 18 -profile:v high -level 4.2 -movflags +faststart $R/master_video.mp4
ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames,width,height,r_frame_rate -of csv=p=0 $R/master_video.mp4
