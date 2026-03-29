# Tutorial: Python on Windows 8.1 - AutoEditsMusicVideoFor2000s

This tutorial shows how to generate a 2000s-style auto-edited music video with the GUI app.

## 1) Start the app
- Double-click `run_windows.bat`, or
- Open Command Prompt in the project folder and run:

```bat
python autoedit_gui.py
```

## 2) Add your source videos
In **Video Sources**:
- Click **Add Multiple Video Files** for direct files, and/or
- Click **Add Video Folder** for full folders.
- Keep **Scan folders recursively** on to include subfolders.

## 3) Add audio
In **Audio Sources**:
- Click **Add Multiple Audio Files**.
- Optional: enable **Use all audio files (shuffle + combine)** for automatic remixed sequence behavior.

## 4) Optional intro/outro sources
Use:
- **Intro Video Sources (optional)** for first clips.
- **Outro Video Sources (optional)** for ending clips.
- Set **Intro clips** and **Outro clips** in settings.

## 5) Configure Mega Deluxe effects
In **Deluxe Generation Settings**:
- Set clip duration range, total clips, resolution, FPS, and CRF.
- Set **Dance mode**, **Audio remix mode**, and **Transition mode**.
- Enable **Auto speed fast+slow** and adjust **Speed min/max**.
- Tune **Loop %**, **Reverse %**, **Stutter %** for automatic effects.
- Enable **Auto-edit to beat** and set **BPM fallback**.

## 6) Generate output
- Choose output path in **Output MP4**.
- Click **Generate Deluxe Music Video**.
- Wait until status shows complete.

## 7) Troubleshooting
- If you get FFmpeg errors, set valid `ffmpeg.exe` and `ffprobe.exe` paths in **FFmpeg Tools**.
- If rendering is slow, enable **10x faster draft mode (AI rough cut)**.
- If output looks too aggressive, lower Dance intensity and effect percentages.
