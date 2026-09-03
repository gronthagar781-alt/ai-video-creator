"""
Subtitle generation module — uses OpenAI Whisper (local) to generate
accurate subtitles from the voice-over audio, with optional translation.
"""

import os
import json
from pathlib import Path
from config import WHISPER_MODEL, WHISPER_LANGUAGE, TEMP_DIR


class SubtitleGenerator:
    """Generate SRT subtitles from audio using Whisper."""

    _model = None  # lazy-loaded

    def __init__(self, model_size: str = None):
        self.model_size = model_size or WHISPER_MODEL

    def _load_model(self):
        if SubtitleGenerator._model is not None:
            return SubtitleGenerator._model

        import whisper
        print(f"[SUB] Loading Whisper model ({self.model_size})...")
        SubtitleGenerator._model = whisper.load_model(self.model_size)
        print("[SUB] Model loaded.")
        return SubtitleGenerator._model

    def generate_srt(
        self,
        audio_path: str,
        output_path: str = None,
        language: str = None,
    ) -> str:
        """
        Generate an SRT subtitle file from an audio file.

        Args:
            audio_path:  Path to the WAV/MP3 audio.
            output_path: Where to save the .srt file.
            language:    "bn" / "hi" or None for auto-detect.

        Returns:
            Path to the .srt file.
        """
        model = self._load_model()

        result = model.transcribe(
            audio_path,
            language=language or WHISPER_LANGUAGE,
            task="transcribe",
            verbose=False,
        )

        if output_path is None:
            output_path = os.path.splitext(audio_path)[0] + ".srt"

        self._write_srt(result["segments"], output_path)
        print(f"[SUB] SRT saved: {output_path}")
        return output_path

    def generate_for_scenes(
        self,
        voice_results: list,
        language: str = None,
        output_dir: str = None,
    ) -> list:
        """
        Generate subtitles for all scene voice-overs.

        Returns list of {"scene_index", "srt_path", "segments"}.
        """
        if output_dir is None:
            output_dir = str(TEMP_DIR / "subtitles")
        os.makedirs(output_dir, exist_ok=True)

        results = []
        for vr in voice_results:
            srt_path = os.path.join(output_dir, f"scene_{vr['scene_index']:03d}.srt")
            self.generate_srt(vr["audio_path"], srt_path, language)
            results.append({
                "scene_index": vr["scene_index"],
                "srt_path": srt_path,
            })

        return results

    def _write_srt(self, segments: list, path: str):
        """Write Whisper segments to SRT format."""
        def _fmt_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds - int(seconds)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        with open(path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                f.write(f"{i}\n")
                f.write(f"{_fmt_time(seg['start'])} --> {_fmt_time(seg['end'])}\n")
                text = seg["text"].strip()
                f.write(f"{text}\n\n")

    def generate_merged_srt(
        self,
        voice_results: list,
        language: str = None,
        output_path: str = None,
    ) -> str:
        """
        Generate a single merged SRT file for the entire video, with
        cumulative timestamps across all scenes.
        """
        model = self._load_model()
        all_segments = []
        time_offset = 0.0

        for vr in voice_results:
            result = model.transcribe(
                vr["audio_path"],
                language=language or WHISPER_LANGUAGE,
                task="transcribe",
                verbose=False,
            )
            for seg in result["segments"]:
                all_segments.append({
                    "start": seg["start"] + time_offset,
                    "end": seg["end"] + time_offset,
                    "text": seg["text"].strip(),
                })
            time_offset += vr["duration"]

        if output_path is None:
            output_path = str(TEMP_DIR / "subtitles_merged.srt")

        self._write_srt(all_segments, output_path)
        print(f"[SUB] Merged SRT: {output_path} ({len(all_segments)} segments)")
        return output_path
