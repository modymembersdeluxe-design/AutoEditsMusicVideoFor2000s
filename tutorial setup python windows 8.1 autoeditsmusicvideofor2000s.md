# Tutorial Setup: Python + Windows 8.1 for AutoEditsMusicVideoFor2000s

This setup guide prepares a Windows 8.1 machine to run the app.

## 1) Install Python
1. Download and install Python (3.8+ recommended for compatibility).
2. During install, enable **Add Python to PATH**.
3. Verify in Command Prompt:

```bat
python --version
```

## 2) Download FFmpeg
1. Download a Windows FFmpeg build that runs on your system.
2. Extract it (example: `C:\ffmpeg`).
3. Verify:

```bat
C:\ffmpeg\bin\ffmpeg.exe -version
C:\ffmpeg\bin\ffprobe.exe -version
```

## 3) Get this project
1. Download ZIP or clone repository.
2. Extract to a folder such as:

```text
D:\AutoEditsMusicVideoFor2000s
```

## 4) Launch app
Use either:

```bat
run_windows.bat
```

or:

```bat
python autoedit_gui.py
```

## 5) First-run configuration
In app:
- Set **ffmpeg.exe** and **ffprobe.exe** in **FFmpeg Tools** (Browse buttons) if not already in PATH.
- Set an output file path.
- Add video/audio sources.

## 6) Recommended starter settings
- Min clip sec: `2.0`
- Max clip sec: `5.0`
- Total clips: `80`
- Resolution: `1280x720`
- FPS: `30`
- CRF: `21`
- Beat sync: enabled
- Fast draft mode: enabled (for quick preview)

## 7) Common issues
- **Python not found**: reinstall Python with PATH option.
- **ffmpeg failed to run**: point to valid exe files via Browse.
- **Very slow export**: lower clip count or enable fast draft mode.
- **No media found in folder**: ensure file extensions are supported and recursive scan is enabled.
