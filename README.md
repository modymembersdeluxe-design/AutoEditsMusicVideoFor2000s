# AutoEditsMusicVideoFor2000s

Simple Python + Tkinter GUI that creates an auto-edited "old internet / 2000s nostalgia" style music video using FFmpeg.

## Features
- Add **multiple video files**.
- Add **multiple folders** (recursive scan for video files).
- Add **multiple audio sources**.
- Set clip length, number of clips, resolution, FPS, and optional random seed.
- Automatically stitches random clips and overlays a selected audio track.

## Requirements
- Python 3.10+
- FFmpeg + FFprobe available in PATH (or select executables in GUI)

## Run
```bash
python autoedit_gui.py
```

## Windows 8.1 notes
- Tkinter is included with most Python installers for Windows.
- Use a recent FFmpeg static build that still runs on your system.
- If ffmpeg/ffprobe are not in PATH, browse to the `.exe` files in the GUI.

## Output
The app exports a single `.mp4` auto-generated music video.
