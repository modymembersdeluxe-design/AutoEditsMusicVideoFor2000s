import shutil
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from autoedit_gui import RenderSettings, gather_videos, run_auto_edit, verify_tool


class SmallAutoEditApp(tk.Tk):
    """Small/basic GUI for quick auto music video edits."""

    def __init__(self):
        super().__init__()
        self.title("AutoEditsMusicVideoFor2000s - Small GUI")
        self.geometry("760x560")

        self.video_files = []
        self.video_folders = []
        self.audio_files = []

        self.ffmpeg_path = tk.StringVar(value=shutil.which("ffmpeg") or "ffmpeg")
        self.ffprobe_path = tk.StringVar(value=shutil.which("ffprobe") or "ffprobe")
        self.output_path = tk.StringVar(value=str(Path.cwd() / "autoedit_small_output.mp4"))

        self.total_clips = tk.StringVar(value="40")
        self.clip_min = tk.StringVar(value="2.0")
        self.clip_max = tk.StringVar(value="5.0")
        self.remix_mode = tk.StringVar(value="Original")
        self.remix_style = tk.StringVar(value="Beat remix")
        self.transition_style = tk.StringVar(value="Fade")
        self.trailer_mode = tk.StringVar(value="Full video")
        self.logo_path = tk.StringVar(value="")

        self.status = tk.StringVar(value="Ready")

        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="AutoEditsMusicVideoFor2000s - Small GUI", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(root, text="Quick mode: minimal options, fast setup.").pack(anchor="w", pady=(0, 8))

        tools = ttk.LabelFrame(root, text="Tools", padding=8)
        tools.pack(fill="x", pady=4)
        self._entry_row(tools, "ffmpeg", self.ffmpeg_path, 0)
        self._entry_row(tools, "ffprobe", self.ffprobe_path, 1)

        src = ttk.LabelFrame(root, text="Sources", padding=8)
        src.pack(fill="both", expand=True, pady=4)

        vbtn = ttk.Frame(src)
        vbtn.pack(fill="x")
        ttk.Button(vbtn, text="Add Video Files", command=self._add_video_files).pack(side="left", padx=(0, 6))
        ttk.Button(vbtn, text="Add Video Folder", command=self._add_video_folder).pack(side="left", padx=(0, 6))
        ttk.Button(vbtn, text="Add Audio Files", command=self._add_audio_files).pack(side="left", padx=(0, 6))
        ttk.Button(vbtn, text="Clear", command=self._clear_sources).pack(side="left")

        self.source_list = tk.Listbox(src, height=11)
        self.source_list.pack(fill="both", expand=True, pady=(8, 0))

        settings = ttk.LabelFrame(root, text="Quick Settings", padding=8)
        settings.pack(fill="x", pady=4)
        self._small_entry(settings, "Total clips", self.total_clips, 0)
        self._small_entry(settings, "Clip min sec", self.clip_min, 1)
        self._small_entry(settings, "Clip max sec", self.clip_max, 2)
        ttk.Label(settings, text="Audio remix mode").grid(row=0, column=2, sticky="w", padx=4, pady=3)
        ttk.Combobox(settings, textvariable=self.remix_mode, values=["Original", "Nightcore", "Slow Jam", "Hyper Dance"], state="readonly", width=16).grid(row=0, column=3, sticky="w", padx=4, pady=3)
        ttk.Label(settings, text="Auto remix style").grid(row=1, column=2, sticky="w", padx=4, pady=3)
        ttk.Combobox(settings, textvariable=self.remix_style, values=["Chaos remix", "Beat remix", "Meme remix", "YouTube Poop", "TikTok", "AMV"], state="readonly", width=16).grid(row=1, column=3, sticky="w", padx=4, pady=3)
        ttk.Label(settings, text="Transition FX").grid(row=2, column=2, sticky="w", padx=4, pady=3)
        ttk.Combobox(settings, textvariable=self.transition_style, values=["Fade", "Glitch", "Warp", "RGB Split"], state="readonly", width=16).grid(row=2, column=3, sticky="w", padx=4, pady=3)
        ttk.Label(settings, text="Trailer mode").grid(row=3, column=0, sticky="w", padx=4, pady=3)
        ttk.Combobox(settings, textvariable=self.trailer_mode, values=["Full video", "Trailer", "Teaser"], state="readonly", width=16).grid(row=3, column=1, sticky="w", padx=4, pady=3)

        out = ttk.LabelFrame(root, text="Output", padding=8)
        out.pack(fill="x", pady=4)
        self._entry_row(out, "Output MP4", self.output_path, 0)
        ttk.Button(out, text="Browse", command=self._pick_output).grid(row=0, column=2, padx=4)
        self._entry_row(out, "Logo/watermark (optional)", self.logo_path, 1)
        ttk.Button(out, text="Browse", command=self._pick_logo).grid(row=1, column=2, padx=4)

        actions = ttk.Frame(root)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Generate (Small GUI)", command=self._generate).pack(side="left")
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=200)
        self.progress.pack(side="left", padx=10)

        ttk.Label(root, textvariable=self.status).pack(anchor="w", pady=6)

    def _entry_row(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(parent, textvariable=var, width=82).grid(row=row, column=1, sticky="ew", padx=4, pady=3)
        parent.columnconfigure(1, weight=1)

    def _small_entry(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(parent, textvariable=var, width=12).grid(row=row, column=1, sticky="w", padx=4, pady=3)

    def _add_video_files(self):
        for p in filedialog.askopenfilenames(title="Select video files"):
            if p not in self.video_files:
                self.video_files.append(p)
        self._refresh_sources()

    def _add_video_folder(self):
        p = filedialog.askdirectory(title="Select video folder")
        if p and p not in self.video_folders:
            self.video_folders.append(p)
        self._refresh_sources()

    def _add_audio_files(self):
        for p in filedialog.askopenfilenames(title="Select audio files"):
            if p not in self.audio_files:
                self.audio_files.append(p)
        self._refresh_sources()

    def _clear_sources(self):
        self.video_files = []
        self.video_folders = []
        self.audio_files = []
        self._refresh_sources()

    def _refresh_sources(self):
        self.source_list.delete(0, "end")
        for p in self.video_files:
            self.source_list.insert("end", f"VIDEO FILE: {p}")
        for p in self.video_folders:
            self.source_list.insert("end", f"VIDEO FOLDER: {p}")
        for p in self.audio_files:
            self.source_list.insert("end", f"AUDIO: {p}")

    def _pick_output(self):
        p = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")], title="Output MP4")
        if p:
            self.output_path.set(p)

    def _pick_logo(self):
        p = filedialog.askopenfilename(title="Logo image", filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp"), ("All files", "*.*")])
        if p:
            self.logo_path.set(p)

    def _generate(self):
        try:
            total = int(self.total_clips.get())
            clip_min = float(self.clip_min.get())
            clip_max = float(self.clip_max.get())
        except ValueError:
            messagebox.showerror("Invalid Settings", "Enter numeric values for clips and durations.")
            return

        videos = gather_videos(self.video_files, self.video_folders, recursive=True)
        audios = [a for a in self.audio_files if Path(a).exists()]
        if not videos:
            messagebox.showerror("Missing Videos", "Add at least one video file/folder.")
            return
        if not audios:
            messagebox.showerror("Missing Audio", "Add at least one audio file.")
            return

        output = self.output_path.get().strip()
        if not output:
            messagebox.showerror("Missing Output", "Choose output MP4 path.")
            return

        try:
            verify_tool(self.ffmpeg_path.get().strip(), "ffmpeg")
            verify_tool(self.ffprobe_path.get().strip(), "ffprobe")
        except RuntimeError as exc:
            messagebox.showerror("Tool Error", str(exc))
            return

        settings = RenderSettings(
            min_clip_duration=max(0.2, clip_min),
            max_clip_duration=max(0.2, clip_max),
            total_clips=max(1, total),
            width=1280,
            height=720,
            fps=30,
            crf=22,
            style_preset="VHS Deluxe",
            transition_mode="Fade",
            transition_duration=0.25,
            dance_intensity=50,
            dance_mode="Auto",
            remix_mode=self.remix_mode.get(),
            auto_beat_sync=True,
            bpm=120.0,
            instant_vfx=True,
            fast_mode=True,
            auto_speed_ramp=True,
            speed_min=0.9,
            speed_max=1.15,
            intro_clip_count=0,
            outro_clip_count=0,
            loop_chance=18,
            reverse_chance=8,
            stutter_chance=14,
            remix_style=self.remix_style.get(),
            transition_style=self.transition_style.get(),
            trailer_mode=self.trailer_mode.get(),
            logo_path=self.logo_path.get().strip(),
            use_all_audio=True,
            random_seed=None,
        )

        if settings.min_clip_duration > settings.max_clip_duration:
            messagebox.showerror("Invalid Settings", "Clip min must be <= clip max.")
            return

        self.status.set("Rendering with small GUI preset...")
        self.progress.start(10)

        def worker():
            try:
                run_auto_edit(
                    ffmpeg_path=self.ffmpeg_path.get().strip(),
                    ffprobe_path=self.ffprobe_path.get().strip(),
                    videos=videos,
                    audios=audios,
                    output_file=output,
                    settings=settings,
                )
                self.after(0, lambda output=output: self._done_ok(output))
            except Exception as exc:
                self.after(0, lambda err=exc: self._done_err(err))

        threading.Thread(target=worker, daemon=True).start()

    def _done_ok(self, output):
        self.progress.stop()
        self.status.set(f"Done: {output}")
        messagebox.showinfo("Done", f"Generated:\n{output}")

    def _done_err(self, exc):
        self.progress.stop()
        self.status.set("Failed")
        messagebox.showerror("Error", str(exc))


if __name__ == "__main__":
    app = SmallAutoEditApp()
    app.mainloop()
