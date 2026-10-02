"""ffprobe metadata with optional Auto-Editor info fallback."""
from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from typing import Any

from .base import Result, Unavailable, command, executable, number


def normalize_ffprobe(data: dict[str, Any]) -> dict[str, Any]:
    videos = [stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"
              and not stream.get("disposition", {}).get("attached_pic")]
    if not videos:
        raise ValueError("no readable video stream")
    video = videos[0]
    audio = [stream for stream in data["streams"] if stream.get("codec_type") == "audio"]
    try:
        duration = number(video.get("duration"))
    except (TypeError, ValueError):
        duration = number(data.get("format", {}).get("duration"))
    if duration <= 0:
        raise ValueError("source duration is unknown or non-positive")
    metadata: dict[str, Any] = {"duration": duration, "width": int(video["width"]),
                                "height": int(video["height"]), "video_codec": video["codec_name"]}
    rate = video.get("avg_frame_rate", "0/1")
    try:
        fps = float(Fraction(rate))
    except (ValueError, ZeroDivisionError):
        fps = 0
    if fps > 0:
        metadata["fps"] = fps
    if audio:
        metadata["audio_codec"] = audio[0]["codec_name"]
    rotation = video.get("tags", {}).get("rotate")
    for side in video.get("side_data_list", []):
        if "rotation" in side:
            rotation = side["rotation"]
    if rotation is not None:
        metadata["rotation"] = number(rotation)
    starts: list[float | None] = []
    for stream in [video, *audio]:
        try:
            starts.append(number(stream.get("start_time")))
        except (TypeError, ValueError):
            starts.append(None)
    metadata["metadata"] = {
        "time_base": video.get("time_base", ""), "audio_streams": len(audio),
        "timestamp_origin_verified": all(start is not None and abs(start) <= 1e-6 for start in starts),
    }
    if starts[0] is not None:
        metadata["metadata"]["start_time"] = starts[0]
    # Different nominal/average rates are a warning signal, not proof of VFR.
    return metadata


def normalize_auto_info(data: dict[str, Any]) -> dict[str, Any]:
    if len(data) != 1:
        raise ValueError("expected metadata for one media file")
    item = next(iter(data.values()))
    video = item.get("video", [])
    if not video:
        raise ValueError("no video stream in Auto-Editor info")
    stream = video[0]
    duration = number(stream.get("duration", item.get("container", {}).get("duration")))
    if duration <= 0:
        raise ValueError("unknown source duration")
    width, height = stream["resolution"]
    metadata: dict[str, Any] = {"duration": duration, "width": int(width), "height": int(height),
                                "video_codec": stream["codec"],
                                "metadata": {"audio_streams": len(item.get("audio", [])),
                                             "timestamp_origin_verified": False}}
    fps = float(Fraction(stream["fps"]))
    if fps > 0:
        metadata["fps"] = fps
    if item.get("audio"):
        metadata["audio_codec"] = item["audio"][0]["codec"]
    return metadata


class MediaProbe:
    name = "media_probe"
    category = "media_probe"
    upstream = "https://ffmpeg.org/ffprobe.html"
    version: str | None = None

    def __init__(self, supplied: dict[str, Any] | None = None):
        self.supplied = supplied or {}
        self.configuration: dict[str, Any] = {"preferred": "ffprobe", "supplied": self.supplied}

    def analyze(self, source: dict[str, Any], timeout: float) -> Result:
        warnings: list[str] = []
        errors: list[str] = []
        try:
            binary = executable("ffprobe")
            self.name = "ffprobe"
            self.version = command([binary, "-version"], timeout, 1024 * 1024).splitlines()[0]
            data = json.loads(command([binary, "-v", "error", "-show_format", "-show_streams",
                                       "-of", "json", source["path"]], timeout))
            metadata = normalize_ffprobe(data)
            if not metadata["metadata"]["timestamp_origin_verified"]:
                warnings.append("Non-zero or unknown stream start times: Auto-Editor activity timing will be skipped.")
            return Result(metadata=metadata, warnings=warnings)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            warnings.append(f"ffprobe unavailable/failed: {exc}")
            if not isinstance(exc, Unavailable):
                errors.append(f"ffprobe: {exc}")
        try:
            binary = executable("auto-editor")
            self.name = "auto-editor-info"
            self.upstream = "https://github.com/WyattBlue/auto-editor"
            self.version = command([binary, "--version"], timeout, 1024 * 1024).strip()
            metadata = normalize_auto_info(json.loads(command(
                [binary, "info", source["path"], "--json"], timeout)))
            warnings.append("Auto-Editor info cannot verify stream timestamp origins; motion/audio evidence skipped.")
            return Result(status="partial", metadata=metadata, warnings=warnings, errors=errors)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            warnings.append(f"Auto-Editor metadata unavailable/failed: {exc}")
            if not isinstance(exc, Unavailable):
                errors.append(f"Auto-Editor info: {exc}")
        if self.supplied:
            self.name = "supplied-metadata"
            self.version = None
            self.upstream = "https://github.com/trinitywellnessnb/workout-remotion-editor"
            return Result(status="partial", metadata=self.supplied, errors=errors, warnings=warnings + [
                "Using supplied metadata; timestamps require manual verification."])
        return Result(status="failed" if errors else "unavailable", errors=errors, warnings=warnings + [
            "No media metadata available. Continue visual/manual analysis; duration remains unknown."])
