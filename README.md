# AutoEditsMusicVideoFor2000s Deluxe

Super Deluxe Python GUI for creating **longer** auto-edited 2000s nostalgia music videos with FFmpeg.

## Deluxe features
- Add **multiple video files** and **multiple video folders**.
- Optional recursive folder scan for large archives.
- Add **multiple audio sources**.
- Audio mode:
  - random one song, or
  - combine all songs (shuffled) before muxing.
- Super-long generation controls:
  - min/max random clip duration,
  - total clip count,
  - resolution, FPS, CRF quality,
  - random seed.
- Style presets: Clean 2000s, VHS Deluxe, CRT Glow, Lo‑Fi Old Net.
- Transition modes: Fade or Cut (with adjustable transition seconds).
- Dance effects control (0-100) to add motion/color energy for dance-style edits.
- Dance mode presets: Auto, Soft, Hard, Off.
- Audio remix modes: Original, Nightcore, Slow Jam, Hyper Dance.
- Auto-edits to the beat (reads TBPM tag when available, otherwise BPM fallback).
- Instant VFX toggle (noise/sharpen/shake style one-click effects).
- 10x faster draft mode for rough-cut turnaround (faster encode preset).

## Requirements
- Python 3.10+
- FFmpeg + FFprobe available in PATH (or manually selected in GUI)

## Run
```bash
python autoedit_gui.py
```

## Windows 8.1 notes
- Tkinter ships with most normal Windows Python installs.
- Use ffmpeg.exe / ffprobe.exe binaries that run on your machine.
- If tools are not in PATH, set them with the GUI Browse buttons.

## Tip for very long videos
Increase **Total clips** (for example 200+) and widen min/max clip seconds.
