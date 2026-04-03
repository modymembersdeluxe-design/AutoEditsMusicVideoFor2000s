import os
import random
import shutil
import subprocess
import tempfile
import threading
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv", ".mpg", ".mpeg"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

STYLE_PRESETS = {
    "Clean 2000s": "eq=saturation=1.18:contrast=1.08",
    "VHS Deluxe": "eq=saturation=1.35:contrast=1.12,noise=alls=9:allf=t+u",
    "CRT Glow": "eq=saturation=1.22:contrast=1.05,unsharp=5:5:0.7:5:5:0.0",
    "Lo-Fi Old Net": "eq=saturation=1.30:contrast=1.15,curves=vintage",
}


@dataclass
class RenderSettings:
    min_clip_duration: float
    max_clip_duration: float
    total_clips: int
    width: int
    height: int
    fps: int
    crf: int
    style_preset: str
    transition_mode: str
    transition_duration: float
    dance_intensity: int
    dance_mode: str
    remix_mode: str
    auto_beat_sync: bool
    bpm: float
    instant_vfx: bool
    fast_mode: bool
    auto_speed_ramp: bool
    speed_min: float
    speed_max: float
    intro_clip_count: int
    outro_clip_count: int
    loop_chance: int
    reverse_chance: int
    stutter_chance: int
    remix_style: str
    transition_style: str
    trailer_mode: str
    logo_path: str
    use_all_audio: bool
    random_seed: Optional[int]


def run_cmd(cmd: List[str], error_label: str):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{error_label}\n{result.stderr.strip()}")
    return result


def verify_tool(tool_path: str, tool_name: str):
    try:
        result = subprocess.run([tool_path, "-version"], capture_output=True, text=True)
    except OSError as exc:
        raise RuntimeError(f"{tool_name} is not executable: {tool_path}") from exc
    if result.returncode != 0:
        raise RuntimeError(f"{tool_name} failed to run. Please select a valid {tool_name} executable.")


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


def probe_bpm_hint(ffprobe_path: str, media_path: str) -> Optional[float]:
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format_tags=TBPM",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        media_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    try:
        bpm = float(raw)
    except ValueError:
        return None
    if 40 <= bpm <= 240:
        return bpm
    return None


def gather_videos(selected_files, selected_folders, recursive=True):
    found = set()
    for file_path in selected_files:
        p = Path(file_path)
        if p.suffix.lower() in VIDEO_EXTENSIONS and p.exists():
            found.add(str(p.resolve()))

    for folder in selected_folders:
        folder_path = Path(folder)
        if not folder_path.exists():
            continue
        if recursive:
            walker = os.walk(folder_path)
        else:
            walker = [(str(folder_path), [], [f.name for f in folder_path.iterdir() if f.is_file()])]
        for root, _, files in walker:
            for file_name in files:
                p = Path(root) / file_name
                if p.suffix.lower() in VIDEO_EXTENSIONS:
                    found.add(str(p.resolve()))
    return sorted(found)


def _build_audio_source(ffmpeg_path: str, ffprobe_path: str, temp_dir: Path, audios: List[str], use_all_audio: bool) -> Tuple[str, float]:
    if not use_all_audio or len(audios) == 1:
        pick = random.choice(audios)
        return pick, probe_duration(ffprobe_path, pick)

    shuffled = audios[:]
    random.shuffle(shuffled)
    list_file = temp_dir / "audio_concat.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for path in shuffled:
            norm = path.replace("\\", "/")
            f.write(f"file '{norm}'\n")

    combined = temp_dir / "audio_combined.mp3"
    run_cmd(
        [
            ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:a",
            "libmp3lame",
            "-q:a",
            "3",
            str(combined),
        ],
        "Failed to combine audio files.",
    )
    return str(combined), probe_duration(ffprobe_path, str(combined))


def build_video_filter(settings: RenderSettings, clip_len: float) -> str:
    style = STYLE_PRESETS.get(settings.style_preset, STYLE_PRESETS["Clean 2000s"])
    filters = [
        f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=decrease",
        f"pad={settings.width}:{settings.height}:(ow-iw)/2:(oh-ih)/2",
        f"fps={settings.fps}",
        style,
    ]

    dance_strength = max(0.0, min(1.0, settings.dance_intensity / 100.0))
    if settings.dance_mode == "Off":
        dance_strength = 0.0
    elif settings.dance_mode == "Soft":
        dance_strength = min(dance_strength, 0.45)
    elif settings.dance_mode == "Hard":
        dance_strength = max(dance_strength, 0.75)
    if dance_strength > 0:
        rot_amt = 0.006 + (0.02 * dance_strength)
        hue_amt = 4 + (14 * dance_strength)
        filters.append(f"rotate={rot_amt:.4f}*sin(2*PI*t*2):fillcolor=black")
        filters.append(f"hue=h={hue_amt:.2f}*sin(2*PI*t)")
        filters.append(f"eq=saturation={1.05 + dance_strength * 0.35:.3f}:contrast={1.03 + dance_strength * 0.17:.3f}")

    if settings.transition_mode == "Fade" and clip_len > 0.3:
        fade_dur = min(settings.transition_duration, clip_len / 2.0)
        fade_out_start = max(0.0, clip_len - fade_dur)
        filters.append(f"fade=t=in:st=0:d={fade_dur:.3f}")
        filters.append(f"fade=t=out:st={fade_out_start:.3f}:d={fade_dur:.3f}")
    elif settings.transition_style == "Glitch":
        filters.append("tblend=all_mode=difference128")
    elif settings.transition_style == "Warp":
        filters.append("vignette=PI/4")

    if settings.instant_vfx:
        filters.append("noise=alls=6:allf=t")
        filters.append("unsharp=5:5:0.6:5:5:0.0")
        if settings.transition_style == "RGB Split":
            filters.append("chromashift=cbh=2:crh=-2")
        if settings.dance_mode != "Off":
            filters.append("rotate=0.007*sin(2*PI*t*4):fillcolor=black")

    return ",".join(filters)


def run_auto_edit(
    ffmpeg_path: str,
    ffprobe_path: str,
    videos: List[str],
    audios: List[str],
    output_file: str,
    settings: RenderSettings,
    intro_videos: Optional[List[str]] = None,
    outro_videos: Optional[List[str]] = None,
):
    if settings.random_seed is not None:
        random.seed(settings.random_seed)
    if not videos:
        raise ValueError("No video clips were selected.")
    if not audios:
        raise ValueError("No audio files were selected.")

    with tempfile.TemporaryDirectory(prefix="autoedit_2000s_deluxe_") as temp_dir:
        temp_path = Path(temp_dir)
        audio_path, audio_duration = _build_audio_source(
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            temp_dir=temp_path,
            audios=audios,
            use_all_audio=settings.use_all_audio,
        )
        bpm_hint = probe_bpm_hint(ffprobe_path, audio_path)
        beat_bpm = bpm_hint if bpm_hint else settings.bpm
        beat_len = 60.0 / max(1.0, beat_bpm)

        total_clips = settings.total_clips
        min_clip = settings.min_clip_duration
        max_clip = settings.max_clip_duration
        auto_beat_sync = settings.auto_beat_sync
        stutter_chance = settings.stutter_chance
        if settings.trailer_mode == "Teaser":
            total_clips = max(12, min(total_clips, 40))
            max_clip = min(max_clip, 2.8)
        elif settings.trailer_mode == "Trailer":
            total_clips = max(20, min(total_clips, 70))
            max_clip = min(max_clip, 3.8)

        if settings.remix_style == "Chaos remix":
            min_clip = max(0.2, min_clip * 0.7)
            max_clip = max(0.6, max_clip * 0.85)
        elif settings.remix_style == "Beat remix":
            auto_beat_sync = True
        elif settings.remix_style == "Meme remix":
            stutter_chance = max(stutter_chance, 35)
            max_clip = min(max_clip, 2.4)

        target_duration = max(audio_duration, total_clips * max_clip)
        concat_file = temp_path / "video_concat.txt"
        segment_files = []
        src_durations: Dict[str, float] = {}
        intro_pool = intro_videos or []
        outro_pool = outro_videos or []
        intro_count = min(settings.intro_clip_count, total_clips)
        outro_count = min(settings.outro_clip_count, max(0, total_clips - intro_count))

        for idx in range(total_clips):
            if idx < intro_count and intro_pool:
                source_video = random.choice(intro_pool)
            elif idx >= total_clips - outro_count and outro_pool:
                source_video = random.choice(outro_pool)
            else:
                source_video = random.choice(videos)
            if source_video in src_durations:
                src_duration = src_durations[source_video]
            else:
                src_duration = probe_duration(ffprobe_path, source_video)
                src_durations[source_video] = src_duration

            if auto_beat_sync:
                beats_per_cut = random.choice([1, 2, 4])
                desired = beat_len * beats_per_cut
                desired = max(min_clip, min(max_clip, desired))
            elif settings.dance_mode == "Auto":
                midpoint = (min_clip + max_clip) / 2.0
                desired = random.triangular(min_clip, max_clip, midpoint * 0.75)
            else:
                desired = random.uniform(min_clip, max_clip)
            clip_len = max(0.15, min(desired, src_duration if src_duration > 0 else desired))
            max_start = max(0.0, src_duration - clip_len)
            start = random.uniform(0.0, max_start) if max_start > 0 else 0.0
            segment_file = temp_path / f"seg_{idx:05d}.mp4"
            vf = build_video_filter(settings=settings, clip_len=clip_len)
            if settings.auto_speed_ramp:
                speed = random.uniform(settings.speed_min, settings.speed_max)
                vf = f"{vf},setpts=PTS/{speed:.3f}"
            if random.randint(1, 100) <= settings.loop_chance:
                vf = f"{vf},tpad=stop_mode=clone:stop_duration=0.15"
            if random.randint(1, 100) <= stutter_chance:
                vf = f"{vf},framestep=2,fps={settings.fps}"
            if random.randint(1, 100) <= settings.reverse_chance and clip_len <= 8:
                vf = f"{vf},reverse"
            run_cmd(
                [
                    ffmpeg_path,
                    "-y",
                    "-ss",
                    f"{start:.3f}",
                    "-t",
                    f"{clip_len:.3f}",
                    "-i",
                    source_video,
                    "-an",
                    "-vf",
                    vf,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast" if settings.fast_mode else "veryfast",
                    "-crf",
                    str(min(30, settings.crf + 4) if settings.fast_mode else settings.crf),
                    "-pix_fmt",
                    "yuv420p",
                    str(segment_file),
                ],
                f"Clip render failed for {source_video}",
            )
            segment_files.append(segment_file)

        with concat_file.open("w", encoding="utf-8") as f:
            for seg in segment_files:
                norm = str(seg).replace("\\", "/")
                f.write(f"file '{norm}'\n")

        stitched = temp_path / "stitched_video.mp4"
        run_cmd(
            [
                ffmpeg_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast" if settings.fast_mode else "veryfast",
                "-crf",
                str(min(30, settings.crf + 4) if settings.fast_mode else settings.crf),
                "-pix_fmt",
                "yuv420p",
                str(stitched),
            ],
            "Failed to stitch generated clips.",
        )

        if settings.logo_path and Path(settings.logo_path).exists():
            branded = temp_path / "stitched_branded.mp4"
            run_cmd(
                [
                    ffmpeg_path,
                    "-y",
                    "-i",
                    str(stitched),
                    "-i",
                    settings.logo_path,
                    "-filter_complex",
                    "overlay=W-w-20:H-h-20",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    str(settings.crf),
                    "-pix_fmt",
                    "yuv420p",
                    str(branded),
                ],
                "Failed to apply logo branding overlay.",
            )
            stitched = branded

        remix_af = None
        if settings.remix_mode == "Nightcore":
            remix_af = "asetrate=44100*1.08,aresample=44100,atempo=1.06,bass=g=2"
        elif settings.remix_mode == "Slow Jam":
            remix_af = "atempo=0.92,volume=1.1,bass=g=3"
        elif settings.remix_mode == "Hyper Dance":
            remix_af = "asetrate=44100*1.12,aresample=44100,atempo=1.08,treble=g=2,bass=g=2"

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
        ]
        if remix_af:
            mux_cmd.extend(["-af", remix_af])
        mux_cmd.extend(
            [
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                output_file,
            ]
        )
        run_cmd(mux_cmd, "Final mux failed.")


class AutoEditApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoEditsMusicVideoFor2000s Deluxe (FFmpeg GUI)")
        self.geometry("1100x860")

        self.video_files = []
        self.video_folders = []
        self.intro_video_files = []
        self.intro_video_folders = []
        self.outro_video_files = []
        self.outro_video_folders = []
        self.audio_files = []

        self.ffmpeg_path = tk.StringVar(value=shutil.which("ffmpeg") or "ffmpeg")
        self.ffprobe_path = tk.StringVar(value=shutil.which("ffprobe") or "ffprobe")
        self.output_path = tk.StringVar(value=str(Path.cwd() / "autoedit_2000s_deluxe.mp4"))

        self.min_clip_duration = tk.StringVar(value="2.0")
        self.max_clip_duration = tk.StringVar(value="6.0")
        self.total_clips = tk.StringVar(value="120")
        self.width = tk.StringVar(value="1280")
        self.height = tk.StringVar(value="720")
        self.fps = tk.StringVar(value="30")
        self.crf = tk.StringVar(value="21")
        self.seed = tk.StringVar(value="")

        self.style_preset = tk.StringVar(value="VHS Deluxe")
        self.transition_mode = tk.StringVar(value="Fade")
        self.transition_duration = tk.StringVar(value="0.25")
        self.dance_intensity = tk.StringVar(value="60")
        self.dance_mode = tk.StringVar(value="Auto")
        self.remix_mode = tk.StringVar(value="Original")
        self.auto_beat_sync = tk.BooleanVar(value=True)
        self.bpm = tk.StringVar(value="120")
        self.instant_vfx = tk.BooleanVar(value=True)
        self.fast_mode = tk.BooleanVar(value=True)
        self.auto_speed_ramp = tk.BooleanVar(value=True)
        self.speed_min = tk.StringVar(value="0.85")
        self.speed_max = tk.StringVar(value="1.20")
        self.intro_clip_count = tk.StringVar(value="4")
        self.outro_clip_count = tk.StringVar(value="4")
        self.loop_chance = tk.StringVar(value="25")
        self.reverse_chance = tk.StringVar(value="12")
        self.stutter_chance = tk.StringVar(value="20")
        self.remix_style = tk.StringVar(value="Beat remix")
        self.transition_style = tk.StringVar(value="Fade")
        self.trailer_mode = tk.StringVar(value="Full video")
        self.logo_path = tk.StringVar(value="")
        self.use_all_audio = tk.BooleanVar(value=True)
        self.scan_recursive = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(
            root,
            text="AutoEditsMusicVideoFor2000s Deluxe - Super Longer Generator",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            root,
            text="Windows 8.1 friendly GUI: AI-style beat sync + instant VFX + multi-source auto music-video builder.",
        ).pack(anchor="w", pady=(0, 10))

        tool_frame = ttk.LabelFrame(root, text="FFmpeg Tools", padding=10)
        tool_frame.pack(fill="x", pady=6)
        self._entry_row(tool_frame, "ffmpeg.exe", self.ffmpeg_path, 0, self._pick_ffmpeg)
        self._entry_row(tool_frame, "ffprobe.exe", self.ffprobe_path, 1, self._pick_ffprobe)

        source_frame = ttk.Frame(root)
        source_frame.pack(fill="both", expand=True)

        videos_frame = ttk.LabelFrame(source_frame, text="Video Sources", padding=10)
        videos_frame.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=6)

        vbtn = ttk.Frame(videos_frame)
        vbtn.pack(fill="x")
        ttk.Button(vbtn, text="Add Multiple Video Files", command=self._add_video_files).pack(side="left", padx=(0, 8))
        ttk.Button(vbtn, text="Add Video Folder", command=self._add_video_folder).pack(side="left", padx=(0, 8))
        ttk.Button(vbtn, text="Clear", command=self._clear_videos).pack(side="left")
        ttk.Checkbutton(videos_frame, text="Scan folders recursively", variable=self.scan_recursive).pack(anchor="w", pady=(6, 0))

        self.video_list = tk.Listbox(videos_frame, height=14)
        self.video_list.pack(fill="both", expand=True, pady=(8, 0))

        audio_frame = ttk.LabelFrame(source_frame, text="Audio Sources", padding=10)
        audio_frame.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=6)

        abtn = ttk.Frame(audio_frame)
        abtn.pack(fill="x")
        ttk.Button(abtn, text="Add Multiple Audio Files", command=self._add_audio_files).pack(side="left", padx=(0, 8))
        ttk.Button(abtn, text="Clear", command=self._clear_audios).pack(side="left")
        ttk.Checkbutton(
            audio_frame,
            text="Use all audio files (shuffle + combine)",
            variable=self.use_all_audio,
        ).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(audio_frame, text="10x faster draft mode (AI rough cut)", variable=self.fast_mode).pack(anchor="w", pady=(2, 0))
        ttk.Checkbutton(audio_frame, text="Instant VFX", variable=self.instant_vfx).pack(anchor="w", pady=(2, 0))
        ttk.Checkbutton(audio_frame, text="Auto-edit to beat", variable=self.auto_beat_sync).pack(anchor="w", pady=(2, 0))

        self.audio_list = tk.Listbox(audio_frame, height=14)
        self.audio_list.pack(fill="both", expand=True, pady=(8, 0))

        io_frame = ttk.Frame(root)
        io_frame.pack(fill="both", expand=True)

        intro_frame = ttk.LabelFrame(io_frame, text="Intro Video Sources (optional)", padding=10)
        intro_frame.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=6)
        ibtn = ttk.Frame(intro_frame)
        ibtn.pack(fill="x")
        ttk.Button(ibtn, text="Add Intro Files", command=self._add_intro_files).pack(side="left", padx=(0, 8))
        ttk.Button(ibtn, text="Add Intro Folder", command=self._add_intro_folder).pack(side="left", padx=(0, 8))
        ttk.Button(ibtn, text="Clear", command=self._clear_intro).pack(side="left")
        self.intro_list = tk.Listbox(intro_frame, height=6)
        self.intro_list.pack(fill="both", expand=True, pady=(8, 0))

        outro_frame = ttk.LabelFrame(io_frame, text="Outro Video Sources (optional)", padding=10)
        outro_frame.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=6)
        obtn = ttk.Frame(outro_frame)
        obtn.pack(fill="x")
        ttk.Button(obtn, text="Add Outro Files", command=self._add_outro_files).pack(side="left", padx=(0, 8))
        ttk.Button(obtn, text="Add Outro Folder", command=self._add_outro_folder).pack(side="left", padx=(0, 8))
        ttk.Button(obtn, text="Clear", command=self._clear_outro).pack(side="left")
        self.outro_list = tk.Listbox(outro_frame, height=6)
        self.outro_list.pack(fill="both", expand=True, pady=(8, 0))

        settings = ttk.LabelFrame(root, text="Deluxe Generation Settings", padding=10)
        settings.pack(fill="x", pady=6)

        self._simple_entry(settings, "Min clip sec", self.min_clip_duration, 0, 0)
        self._simple_entry(settings, "Max clip sec", self.max_clip_duration, 0, 2)
        self._simple_entry(settings, "Total clips (long video)", self.total_clips, 0, 4)
        self._simple_entry(settings, "Width", self.width, 1, 0)
        self._simple_entry(settings, "Height", self.height, 1, 2)
        self._simple_entry(settings, "FPS", self.fps, 1, 4)
        self._simple_entry(settings, "CRF quality", self.crf, 2, 0)
        self._simple_entry(settings, "Random seed", self.seed, 2, 2)
        self._simple_entry(settings, "Transition sec", self.transition_duration, 3, 0)
        self._simple_entry(settings, "Dance intensity (0-100)", self.dance_intensity, 3, 2)
        self._simple_entry(settings, "BPM fallback", self.bpm, 3, 4)
        self._simple_entry(settings, "Intro clips", self.intro_clip_count, 5, 0)
        self._simple_entry(settings, "Outro clips", self.outro_clip_count, 5, 2)
        self._simple_entry(settings, "Speed min", self.speed_min, 6, 0)
        self._simple_entry(settings, "Speed max", self.speed_max, 6, 2)
        self._simple_entry(settings, "Loop %", self.loop_chance, 7, 0)
        self._simple_entry(settings, "Reverse %", self.reverse_chance, 7, 2)
        self._simple_entry(settings, "Stutter %", self.stutter_chance, 7, 4)

        ttk.Label(settings, text="Style preset").grid(row=2, column=4, sticky="w", padx=6, pady=5)
        ttk.Combobox(
            settings,
            textvariable=self.style_preset,
            values=list(STYLE_PRESETS.keys()),
            state="readonly",
            width=22,
        ).grid(row=2, column=5, sticky="w", padx=6, pady=5)
        ttk.Label(settings, text="Transition mode").grid(row=3, column=4, sticky="w", padx=6, pady=5)
        ttk.Combobox(
            settings,
            textvariable=self.transition_mode,
            values=["Fade", "Cut"],
            state="readonly",
            width=22,
        ).grid(row=3, column=5, sticky="w", padx=6, pady=5)
        ttk.Label(settings, text="Dance mode").grid(row=4, column=0, sticky="w", padx=6, pady=5)
        ttk.Combobox(
            settings,
            textvariable=self.dance_mode,
            values=["Auto", "Soft", "Hard", "Off"],
            state="readonly",
            width=20,
        ).grid(row=4, column=1, sticky="w", padx=6, pady=5)
        ttk.Label(settings, text="Audio remix mode").grid(row=4, column=2, sticky="w", padx=6, pady=5)
        ttk.Combobox(
            settings,
            textvariable=self.remix_mode,
            values=["Original", "Nightcore", "Slow Jam", "Hyper Dance"],
            state="readonly",
            width=20,
        ).grid(row=4, column=3, sticky="w", padx=6, pady=5)
        ttk.Label(settings, text="Auto remix style").grid(row=5, column=4, sticky="w", padx=6, pady=5)
        ttk.Combobox(
            settings,
            textvariable=self.remix_style,
            values=["Chaos remix", "Beat remix", "Meme remix", "YouTube Poop", "TikTok", "AMV"],
            state="readonly",
            width=22,
        ).grid(row=5, column=5, sticky="w", padx=6, pady=5)
        ttk.Label(settings, text="Transition FX").grid(row=6, column=4, sticky="w", padx=6, pady=5)
        ttk.Combobox(
            settings,
            textvariable=self.transition_style,
            values=["Fade", "Glitch", "Warp", "RGB Split"],
            state="readonly",
            width=22,
        ).grid(row=6, column=5, sticky="w", padx=6, pady=5)
        ttk.Label(settings, text="Trailer mode").grid(row=7, column=4, sticky="w", padx=6, pady=5)
        ttk.Combobox(
            settings,
            textvariable=self.trailer_mode,
            values=["Full video", "Trailer", "Teaser"],
            state="readonly",
            width=22,
        ).grid(row=7, column=5, sticky="w", padx=6, pady=5)
        ttk.Checkbutton(settings, text="Auto speed fast+slow", variable=self.auto_speed_ramp).grid(row=8, column=4, columnspan=2, sticky="w", padx=6, pady=5)

        output_frame = ttk.LabelFrame(root, text="Output", padding=10)
        output_frame.pack(fill="x", pady=6)
        self._entry_row(output_frame, "Output MP4", self.output_path, 0, self._pick_output)
        self._entry_row(output_frame, "Logo / watermark PNG (optional)", self.logo_path, 1, self._pick_logo)

        preset_row = ttk.Frame(root)
        preset_row.pack(fill="x", pady=(4, 0))
        ttk.Button(preset_row, text="Save preset", command=self._save_preset).pack(side="left", padx=(0, 8))
        ttk.Button(preset_row, text="Load preset", command=self._load_preset).pack(side="left")

        action_row = ttk.Frame(root)
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="Generate Deluxe Music Video", command=self._generate).pack(side="left")

        self.progress = ttk.Progressbar(action_row, mode="indeterminate", length=240)
        self.progress.pack(side="left", padx=10)

        self.status = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status, foreground="#004a80").pack(anchor="w", pady=6)

    def _simple_entry(self, parent, label, var, row, col):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=6, pady=5)
        ttk.Entry(parent, textvariable=var, width=12).grid(row=row, column=col + 1, sticky="w", padx=6, pady=5)

    def _entry_row(self, parent, label, var, row, browse_command):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(parent, textvariable=var, width=108).grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)
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

    def _add_intro_files(self):
        files = filedialog.askopenfilenames(title="Select intro video files")
        for file in files:
            if file not in self.intro_video_files:
                self.intro_video_files.append(file)
        self._refresh_intro_list()

    def _add_intro_folder(self):
        folder = filedialog.askdirectory(title="Select intro video folder")
        if folder and folder not in self.intro_video_folders:
            self.intro_video_folders.append(folder)
        self._refresh_intro_list()

    def _clear_intro(self):
        self.intro_video_files = []
        self.intro_video_folders = []
        self._refresh_intro_list()

    def _add_outro_files(self):
        files = filedialog.askopenfilenames(title="Select outro video files")
        for file in files:
            if file not in self.outro_video_files:
                self.outro_video_files.append(file)
        self._refresh_outro_list()

    def _add_outro_folder(self):
        folder = filedialog.askdirectory(title="Select outro video folder")
        if folder and folder not in self.outro_video_folders:
            self.outro_video_folders.append(folder)
        self._refresh_outro_list()

    def _clear_outro(self):
        self.outro_video_files = []
        self.outro_video_folders = []
        self._refresh_outro_list()

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

    def _refresh_intro_list(self):
        self.intro_list.delete(0, "end")
        for file in self.intro_video_files:
            self.intro_list.insert("end", f"FILE: {file}")
        for folder in self.intro_video_folders:
            self.intro_list.insert("end", f"FOLDER: {folder}")

    def _refresh_outro_list(self):
        self.outro_list.delete(0, "end")
        for file in self.outro_video_files:
            self.outro_list.insert("end", f"FILE: {file}")
        for folder in self.outro_video_folders:
            self.outro_list.insert("end", f"FOLDER: {folder}")

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

    def _pick_logo(self):
        path = filedialog.askopenfilename(title="Select logo/watermark image", filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp"), ("All files", "*.*")])
        if path:
            self.logo_path.set(path)

    def _save_preset(self):
        path = filedialog.asksaveasfilename(title="Save preset JSON", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = {
            "min_clip_duration": self.min_clip_duration.get(),
            "max_clip_duration": self.max_clip_duration.get(),
            "total_clips": self.total_clips.get(),
            "width": self.width.get(),
            "height": self.height.get(),
            "fps": self.fps.get(),
            "crf": self.crf.get(),
            "transition_mode": self.transition_mode.get(),
            "transition_duration": self.transition_duration.get(),
            "transition_style": self.transition_style.get(),
            "remix_style": self.remix_style.get(),
            "trailer_mode": self.trailer_mode.get(),
            "dance_intensity": self.dance_intensity.get(),
            "dance_mode": self.dance_mode.get(),
            "remix_mode": self.remix_mode.get(),
            "bpm": self.bpm.get(),
            "speed_min": self.speed_min.get(),
            "speed_max": self.speed_max.get(),
            "loop_chance": self.loop_chance.get(),
            "reverse_chance": self.reverse_chance.get(),
            "stutter_chance": self.stutter_chance.get(),
            "logo_path": self.logo_path.get(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Preset saved", f"Preset saved to:\n{path}")

    def _load_preset(self):
        path = filedialog.askopenfilename(title="Load preset JSON", filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, var in [
            ("min_clip_duration", self.min_clip_duration),
            ("max_clip_duration", self.max_clip_duration),
            ("total_clips", self.total_clips),
            ("width", self.width),
            ("height", self.height),
            ("fps", self.fps),
            ("crf", self.crf),
            ("transition_mode", self.transition_mode),
            ("transition_duration", self.transition_duration),
            ("transition_style", self.transition_style),
            ("remix_style", self.remix_style),
            ("trailer_mode", self.trailer_mode),
            ("dance_intensity", self.dance_intensity),
            ("dance_mode", self.dance_mode),
            ("remix_mode", self.remix_mode),
            ("bpm", self.bpm),
            ("speed_min", self.speed_min),
            ("speed_max", self.speed_max),
            ("loop_chance", self.loop_chance),
            ("reverse_chance", self.reverse_chance),
            ("stutter_chance", self.stutter_chance),
            ("logo_path", self.logo_path),
        ]:
            if key in data:
                var.set(str(data[key]))
        messagebox.showinfo("Preset loaded", f"Loaded preset:\n{path}")

    def _set_busy(self, busy: bool):
        if busy:
            self.progress.start(10)
        else:
            self.progress.stop()

    def _read_settings(self) -> RenderSettings:
        min_clip = float(self.min_clip_duration.get())
        max_clip = float(self.max_clip_duration.get())
        if min_clip <= 0 or max_clip <= 0:
            raise ValueError("Clip duration values must be positive.")
        if min_clip > max_clip:
            raise ValueError("Min clip duration cannot be greater than max clip duration.")

        total_clips = int(self.total_clips.get())
        if total_clips < 1:
            raise ValueError("Total clips must be at least 1.")

        width = int(self.width.get())
        height = int(self.height.get())
        fps = int(self.fps.get())
        crf = int(self.crf.get())
        if not (1 <= crf <= 40):
            raise ValueError("CRF must be between 1 and 40.")
        transition_duration = float(self.transition_duration.get())
        if transition_duration < 0:
            raise ValueError("Transition duration cannot be negative.")
        dance_intensity = int(self.dance_intensity.get())
        if not (0 <= dance_intensity <= 100):
            raise ValueError("Dance intensity must be between 0 and 100.")
        if self.dance_mode.get() not in {"Auto", "Soft", "Hard", "Off"}:
            raise ValueError("Invalid dance mode.")
        if self.remix_mode.get() not in {"Original", "Nightcore", "Slow Jam", "Hyper Dance"}:
            raise ValueError("Invalid remix mode.")
        if self.remix_style.get() not in {"Chaos remix", "Beat remix", "Meme remix", "YouTube Poop", "TikTok", "AMV"}:
            raise ValueError("Invalid auto remix style.")
        if self.transition_style.get() not in {"Fade", "Glitch", "Warp", "RGB Split"}:
            raise ValueError("Invalid transition FX style.")
        if self.trailer_mode.get() not in {"Full video", "Trailer", "Teaser"}:
            raise ValueError("Invalid trailer mode.")
        bpm = float(self.bpm.get())
        if bpm < 40 or bpm > 240:
            raise ValueError("BPM fallback must be between 40 and 240.")
        speed_min = float(self.speed_min.get())
        speed_max = float(self.speed_max.get())
        if speed_min <= 0 or speed_max <= 0:
            raise ValueError("Speed min/max must be greater than 0.")
        if speed_min > speed_max:
            raise ValueError("Speed min cannot exceed speed max.")
        intro_clip_count = int(self.intro_clip_count.get())
        outro_clip_count = int(self.outro_clip_count.get())
        if intro_clip_count < 0 or outro_clip_count < 0:
            raise ValueError("Intro/Outro clip count cannot be negative.")
        loop_chance = int(self.loop_chance.get())
        reverse_chance = int(self.reverse_chance.get())
        stutter_chance = int(self.stutter_chance.get())
        for label, value in {"Loop": loop_chance, "Reverse": reverse_chance, "Stutter": stutter_chance}.items():
            if value < 0 or value > 100:
                raise ValueError(f"{label} chance must be between 0 and 100.")

        seed = int(self.seed.get()) if self.seed.get().strip() else None
        return RenderSettings(
            min_clip_duration=min_clip,
            max_clip_duration=max_clip,
            total_clips=total_clips,
            width=width,
            height=height,
            fps=fps,
            crf=crf,
            style_preset=self.style_preset.get(),
            transition_mode=self.transition_mode.get(),
            transition_duration=transition_duration,
            dance_intensity=dance_intensity,
            dance_mode=self.dance_mode.get(),
            remix_mode=self.remix_mode.get(),
            auto_beat_sync=self.auto_beat_sync.get(),
            bpm=bpm,
            instant_vfx=self.instant_vfx.get(),
            fast_mode=self.fast_mode.get(),
            auto_speed_ramp=self.auto_speed_ramp.get(),
            speed_min=speed_min,
            speed_max=speed_max,
            intro_clip_count=intro_clip_count,
            outro_clip_count=outro_clip_count,
            loop_chance=loop_chance,
            reverse_chance=reverse_chance,
            stutter_chance=stutter_chance,
            remix_style=self.remix_style.get(),
            transition_style=self.transition_style.get(),
            trailer_mode=self.trailer_mode.get(),
            logo_path=self.logo_path.get().strip(),
            use_all_audio=self.use_all_audio.get(),
            random_seed=seed,
        )

    def _generate(self):
        try:
            settings = self._read_settings()
        except ValueError as exc:
            messagebox.showerror("Invalid Settings", str(exc))
            return

        videos = gather_videos(self.video_files, self.video_folders, recursive=self.scan_recursive.get())
        intro_videos = gather_videos(self.intro_video_files, self.intro_video_folders, recursive=self.scan_recursive.get())
        outro_videos = gather_videos(self.outro_video_files, self.outro_video_folders, recursive=self.scan_recursive.get())
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
        try:
            verify_tool(self.ffmpeg_path.get().strip(), "ffmpeg")
            verify_tool(self.ffprobe_path.get().strip(), "ffprobe")
        except RuntimeError as exc:
            messagebox.showerror("FFmpeg/FFprobe Error", str(exc))
            return

        self.status.set("Generating deluxe music video... this can take time for super long videos.")
        self._set_busy(True)

        def worker():
            try:
                run_auto_edit(
                    ffmpeg_path=self.ffmpeg_path.get().strip(),
                    ffprobe_path=self.ffprobe_path.get().strip(),
                    videos=videos,
                    audios=audios,
                    output_file=output,
                    settings=settings,
                    intro_videos=intro_videos,
                    outro_videos=outro_videos,
                )
                self.after(0, lambda output=output: self._done_success(output))
            except Exception as exc:
                self.after(0, lambda err=exc: self._done_error(err))

        threading.Thread(target=worker, daemon=True).start()

    def _done_success(self, output):
        self._set_busy(False)
        self.status.set(f"Done: {output}")
        messagebox.showinfo("Success", f"Deluxe music video generated:\n{output}")

    def _done_error(self, exc):
        self._set_busy(False)
        self.status.set("Failed")
        messagebox.showerror("AutoEdit Error", str(exc))


if __name__ == "__main__":
    app = AutoEditApp()
    app.mainloop()
