import json
import os
import random
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv", ".mpg", ".mpeg"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def probe_duration(ffprobe_path: str, media_path: str) -> float:
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        media_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {media_path}: {result.stderr.strip()}")
    return max(0.0, float(result.stdout.strip() or "0"))


def gather_videos(selected_files, selected_folders):
    found = set()
    for file_path in selected_files:
        p = Path(file_path)
        if p.suffix.lower() in VIDEO_EXTENSIONS and p.exists():
            found.add(str(p.resolve()))
    for folder in selected_folders:
        folder_path = Path(folder)
        if not folder_path.exists():
            continue
        for root, _, files in os.walk(folder_path):
            for file_name in files:
                p = Path(root) / file_name
                if p.suffix.lower() in VIDEO_EXTENSIONS:
                    found.add(str(p.resolve()))
    return sorted(found)


def run_auto_edit(
    ffmpeg_path: str,
    ffprobe_path: str,
    videos,
    audios,
    output_file: str,
    clip_duration: float,
    total_clips: int,
    width: int,
    height: int,
    fps: int,
    random_seed: int | None,
):
    if random_seed is not None:
        random.seed(random_seed)

    if not videos:
        raise ValueError("No video clips were selected.")
    if not audios:
        raise ValueError("No audio sources were selected.")

    audio_path = random.choice(audios)
    audio_duration = probe_duration(ffprobe_path, audio_path)
    target_duration = max(audio_duration, clip_duration * total_clips)

    with tempfile.TemporaryDirectory(prefix="autoedit_2000s_") as temp_dir:
        temp_dir_path = Path(temp_dir)
        list_file = temp_dir_path / "concat_list.txt"
        segment_paths = []

        for i in range(total_clips):
            source_video = random.choice(videos)
            source_duration = probe_duration(ffprobe_path, source_video)
            safe_len = max(0.1, min(clip_duration, source_duration if source_duration > 0 else clip_duration))
            max_start = max(0.0, source_duration - safe_len)
            start = random.uniform(0.0, max_start) if max_start > 0 else 0.0
            segment_path = temp_dir_path / f"seg_{i:04d}.mp4"

            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps},eq=saturation=1.25:contrast=1.08"
            )
            cmd = [
                ffmpeg_path,
                "-y",
                "-ss",
                f"{start:.3f}",
                "-t",
                f"{safe_len:.3f}",
                "-i",
                source_video,
                "-an",
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "21",
                "-pix_fmt",
                "yuv420p",
                str(segment_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Segment render failed for {source_video}\n{result.stderr}")

            segment_paths.append(segment_path)

        with list_file.open("w", encoding="utf-8") as f:
            for p in segment_paths:
                norm = str(p).replace('\\', '/')
                f.write(f"file '{norm}'\n")

        stitched = temp_dir_path / "stitched.mp4"
        concat_cmd = [
            ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            str(stitched),
        ]
        concat_result = subprocess.run(concat_cmd, capture_output=True, text=True)
        if concat_result.returncode != 0:
            raise RuntimeError(f"Concat failed\n{concat_result.stderr}")

        mux_cmd = [
            ffmpeg_path,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            audio_path,
            "-i",
            str(stitched),
            "-map",
            "1:v:0",
            "-map",
            "0:a:0",
            "-t",
            f"{target_duration:.3f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            output_file,
        ]
        mux_result = subprocess.run(mux_cmd, capture_output=True, text=True)
        if mux_result.returncode != 0:
            raise RuntimeError(f"Audio mux failed\n{mux_result.stderr}")


class AutoEditApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoEdit 2000s Music Video (FFmpeg GUI)")
        self.geometry("980x740")

        self.video_files = []
        self.video_folders = []
        self.audio_files = []

        self.ffmpeg_path = tk.StringVar(value=shutil.which("ffmpeg") or "ffmpeg")
        self.ffprobe_path = tk.StringVar(value=shutil.which("ffprobe") or "ffprobe")
        self.output_path = tk.StringVar(value=str(Path.cwd() / "autoedit_2000s_musicvideo.mp4"))

        self.clip_duration = tk.StringVar(value="4")
        self.total_clips = tk.StringVar(value="45")
        self.width = tk.StringVar(value="1280")
        self.height = tk.StringVar(value="720")
        self.fps = tk.StringVar(value="30")
        self.seed = tk.StringVar(value="")

        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="AutoEdit: old internet / 2000s nostalgia music video", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(root, text="Select many videos + folders + many audio files, then generate one auto-edited music video.").pack(anchor="w", pady=(0, 10))

        tool_frame = ttk.LabelFrame(root, text="FFmpeg Tools", padding=10)
        tool_frame.pack(fill="x", pady=6)
        self._entry_row(tool_frame, "ffmpeg path", self.ffmpeg_path, 0, self._pick_ffmpeg)
        self._entry_row(tool_frame, "ffprobe path", self.ffprobe_path, 1, self._pick_ffprobe)

        videos_frame = ttk.LabelFrame(root, text="Video Sources", padding=10)
        videos_frame.pack(fill="both", expand=True, pady=6)

        btn_row = ttk.Frame(videos_frame)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Add Multiple Video Files", command=self._add_video_files).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Add Video Folder", command=self._add_video_folder).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Clear", command=self._clear_videos).pack(side="left")

        self.video_list = tk.Listbox(videos_frame, height=10)
        self.video_list.pack(fill="both", expand=True, pady=(8, 0))

        audio_frame = ttk.LabelFrame(root, text="Audio Sources", padding=10)
        audio_frame.pack(fill="both", expand=True, pady=6)

        audio_btn_row = ttk.Frame(audio_frame)
        audio_btn_row.pack(fill="x")
        ttk.Button(audio_btn_row, text="Add Multiple Audio Files", command=self._add_audio_files).pack(side="left", padx=(0, 8))
        ttk.Button(audio_btn_row, text="Clear", command=self._clear_audios).pack(side="left")

        self.audio_list = tk.Listbox(audio_frame, height=6)
        self.audio_list.pack(fill="both", expand=True, pady=(8, 0))

        settings = ttk.LabelFrame(root, text="Generation Settings", padding=10)
        settings.pack(fill="x", pady=6)

        self._simple_entry(settings, "Clip length (seconds)", self.clip_duration, 0, 0)
        self._simple_entry(settings, "Number of clips", self.total_clips, 0, 2)
        self._simple_entry(settings, "Width", self.width, 1, 0)
        self._simple_entry(settings, "Height", self.height, 1, 2)
        self._simple_entry(settings, "FPS", self.fps, 2, 0)
        self._simple_entry(settings, "Random seed (optional)", self.seed, 2, 2)

        output_frame = ttk.LabelFrame(root, text="Output", padding=10)
        output_frame.pack(fill="x", pady=6)
        self._entry_row(output_frame, "Output MP4", self.output_path, 0, self._pick_output)

        action_row = ttk.Frame(root)
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="Generate Music Video", command=self._generate).pack(side="left")

        self.progress = ttk.Progressbar(action_row, mode="indeterminate", length=200)
        self.progress.pack(side="left", padx=10)

        self.status = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status).pack(anchor="w", pady=6)

    def _simple_entry(self, parent, label, var, row, col):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=6, pady=5)
        ttk.Entry(parent, textvariable=var, width=14).grid(row=row, column=col + 1, sticky="w", padx=6, pady=5)

    def _entry_row(self, parent, label, var, row, browse_command):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(parent, textvariable=var, width=96).grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Button(parent, text="Browse", command=browse_command).grid(row=row, column=2, pady=4)
        parent.columnconfigure(1, weight=1)

    def _add_video_files(self):
        files = filedialog.askopenfilenames(title="Select video files")
        for file in files:
            if file not in self.video_files:
                self.video_files.append(file)
        self._refresh_video_list()

    def _add_video_folder(self):
        folder = filedialog.askdirectory(title="Select video folder")
        if folder and folder not in self.video_folders:
            self.video_folders.append(folder)
        self._refresh_video_list()

    def _clear_videos(self):
        self.video_files = []
        self.video_folders = []
        self._refresh_video_list()

    def _add_audio_files(self):
        files = filedialog.askopenfilenames(title="Select audio files")
        for file in files:
            if Path(file).suffix.lower() in AUDIO_EXTENSIONS and file not in self.audio_files:
                self.audio_files.append(file)
        self._refresh_audio_list()

    def _clear_audios(self):
        self.audio_files = []
        self._refresh_audio_list()

    def _refresh_video_list(self):
        self.video_list.delete(0, "end")
        for file in self.video_files:
            self.video_list.insert("end", f"FILE: {file}")
        for folder in self.video_folders:
            self.video_list.insert("end", f"FOLDER: {folder}")

    def _refresh_audio_list(self):
        self.audio_list.delete(0, "end")
        for file in self.audio_files:
            self.audio_list.insert("end", file)

    def _pick_output(self):
        path = filedialog.asksaveasfilename(title="Output MP4", defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if path:
            self.output_path.set(path)

    def _pick_ffmpeg(self):
        path = filedialog.askopenfilename(title="Select ffmpeg executable")
        if path:
            self.ffmpeg_path.set(path)

    def _pick_ffprobe(self):
        path = filedialog.askopenfilename(title="Select ffprobe executable")
        if path:
            self.ffprobe_path.set(path)

    def _set_busy(self, busy: bool):
        if busy:
            self.progress.start(10)
        else:
            self.progress.stop()

    def _generate(self):
        try:
            clip_duration = float(self.clip_duration.get())
            total_clips = int(self.total_clips.get())
            width = int(self.width.get())
            height = int(self.height.get())
            fps = int(self.fps.get())
            seed = int(self.seed.get()) if self.seed.get().strip() else None
        except ValueError:
            messagebox.showerror("Invalid Settings", "Please enter valid numbers in settings fields.")
            return

        videos = gather_videos(self.video_files, self.video_folders)
        audios = [a for a in self.audio_files if Path(a).exists()]
        if not videos:
            messagebox.showerror("Missing Videos", "Please add at least one valid video file or folder.")
            return
        if not audios:
            messagebox.showerror("Missing Audio", "Please add at least one valid audio file.")
            return

        output = self.output_path.get().strip()
        if not output:
            messagebox.showerror("Missing Output", "Please choose output file path.")
            return

        self.status.set("Generating auto-edited music video...")
        self._set_busy(True)

        def worker():
            try:
                run_auto_edit(
                    ffmpeg_path=self.ffmpeg_path.get().strip(),
                    ffprobe_path=self.ffprobe_path.get().strip(),
                    videos=videos,
                    audios=audios,
                    output_file=output,
                    clip_duration=clip_duration,
                    total_clips=total_clips,
                    width=width,
                    height=height,
                    fps=fps,
                    random_seed=seed,
                )
                self.after(0, lambda: self._done_success(output))
            except Exception as exc:
                self.after(0, lambda: self._done_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _done_success(self, output):
        self._set_busy(False)
        self.status.set(f"Done: {output}")
        messagebox.showinfo("Success", f"Music video generated:\n{output}")

    def _done_error(self, exc):
        self._set_busy(False)
        self.status.set("Failed")
        messagebox.showerror("AutoEdit Error", str(exc))


if __name__ == "__main__":
    app = AutoEditApp()
    app.mainloop()
