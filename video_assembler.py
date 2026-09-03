"""
Video assembly module — combines AI-generated video clips with voice-over audio
and subtitles into the final video using FFmpeg.

Pipeline per scene:
  1. Concatenate scene clips (if multiple) → single clip per scene
  2. Trim/loop video to match voice-over duration
  3. Add voice-over audio
  4. Burn in subtitles
  5. Concatenate all scenes → final video

The final output is an MP4 ready for YouTube/Facebook upload.
"""

import os
import subprocess
import json
from pathlib import Path
from config import FFMPEG_BINARY, FFPROBE_BINARY, VIDEO_FPS, TEMP_DIR, OUTPUT_DIR


class VideoAssembler:
    """Assembles final video from clips, audio, and subtitles."""

    def __init__(self):
        self.ffmpeg = FFMPEG_BINARY
        self.ffprobe = FFPROBE_BINARY

    def _run(self, cmd: list) -> str:
        """Run a command and return stdout."""
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"CMD: {' '.join(cmd[:20])}...")
            print(f"STDERR: {result.stderr[:500]}")
            raise RuntimeError(f"FFmpeg command failed: {result.stderr[:200]}")
        return result.stdout

    def _get_duration(self, media_path: str) -> float:
        """Get duration of a media file in seconds."""
        cmd = [
            self.ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            media_path,
        ]
        out = self._run(cmd).strip()
        return float(out)

    def _concat_clips(self, clip_paths: list, output_path: str) -> str:
        """Concatenate multiple video clips into one."""
        if len(clip_paths) == 1:
            return clip_paths[0]

        # Create concat list file
        list_file = output_path + ".txt"
        with open(list_file, "w") as f:
            for cp in clip_paths:
                # Use absolute path
                f.write(f"file '{os.path.abspath(cp)}'\n")

        cmd = [
            self.ffmpeg, "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_path,
        ]
        self._run(cmd)
        return output_path

    def _fit_video_to_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> str:
        """
        Adjust video duration to match audio:
        - If video is shorter → loop (with crossfade)
        - If video is longer → trim
        Then add the audio track.
        """
        audio_dur = self._get_duration(audio_path)
        video_dur = self._get_duration(video_path)

        if video_dur < audio_dur:
            # Loop the video to fill audio duration
            loops = int(audio_dur / video_dur) + 1
            cmd = [
                self.ffmpeg, "-y",
                "-stream_loop", str(loops),
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-pix_fmt", "yuv420p",
                "-r", str(VIDEO_FPS),
                output_path,
            ]
        else:
            # Trim video to audio length
            cmd = [
                self.ffmpeg, "-y",
                "-i", video_path,
                "-i", audio_path,
                "-t", str(audio_dur),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-r", str(VIDEO_FPS),
                "-map", "0:v:0",
                "-map", "1:a:0",
                output_path,
            ]
        self._run(cmd)
        return output_path

    def _burn_subtitles(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        style: str = None,
    ) -> str:
        """Burn SRT subtitles into video."""
        if not os.path.exists(srt_path):
            # Skip if no subtitle file
            return video_path

        if style is None:
            # Bengali/Hindi subtitle styling — white text, black outline
            style = (
                "FontName=Noto Sans Bengali,"
                "FontSize=7,"
                "PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,"
                "BackColour=&H80000000,"
                "BorderStyle=1,"
                "Outline=2,"
                "Shadow=1,"
                "Alignment=2,"
                "MarginV=25"
            )

        # Escape path for FFmpeg subtitles filter
        srt_escaped = srt_path.replace("\\", "\\\\").replace(":", "\\:")
        srt_escaped = srt_escaped.replace("'", "\\'")

        cmd = [
            self.ffmpeg, "-y",
            "-i", video_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "medium",
            "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        self._run(cmd)
        return output_path

    def _concat_scenes(self, scene_videos: list, output_path: str) -> str:
        """Concatenate all scene videos into the final video."""
        list_file = output_path + ".txt"
        with open(list_file, "w") as f:
            for sv in scene_videos:
                f.write(f"file '{os.path.abspath(sv)}'\n")

        cmd = [
            self.ffmpeg, "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_path,
        ]
        self._run(cmd)
        return output_path

    def assemble(
        self,
        video_results: list,
        voice_results: list,
        subtitle_results: list = None,
        title: str = "output",
        burn_subs: bool = True,
    ) -> str:
        """
        Full assembly pipeline: merge video clips + audio + subtitles → final MP4.

        Args:
            video_results:     List of {scene_index, clip_paths[]}
            voice_results:     List of {scene_index, audio_path, duration}
            subtitle_results:  List of {scene_index, srt_path}
            title:             Output filename (without extension).
            burn_subs:         Whether to burn subtitles into video.

        Returns:
            Path to the final MP4.
        """
        work_dir = str(TEMP_DIR / "assembly")
        os.makedirs(work_dir, exist_ok=True)

        # Build lookup maps
        voice_map = {v["scene_index"]: v for v in voice_results}
        sub_map = {}
        if subtitle_results:
            sub_map = {s["scene_index"]: s for s in subtitle_results}

        scene_final_videos = []

        for vr in video_results:
            idx = vr["scene_index"]
            clips = vr["clip_paths"]
            audio = voice_map.get(idx, {}).get("audio_path")
            srt = sub_map.get(idx, {}).get("srt_path")

            if not audio:
                print(f"[ASSY] No audio for scene {idx}, skipping.")
                continue

            # Step 1: Concat scene clips
            merged_clip = os.path.join(work_dir, f"scene_{idx:03d}_merged.mp4")
            if len(clips) > 1:
                self._concat_clips(clips, merged_clip)
            else:
                merged_clip = clips[0]

            # Step 2: Fit video to audio duration + add audio
            with_audio = os.path.join(work_dir, f"scene_{idx:03d}_audio.mp4")
            self._fit_video_to_audio(merged_clip, audio, with_audio)

            # Step 3: Burn subtitles
            if burn_subs and srt and os.path.exists(srt):
                with_subs = os.path.join(work_dir, f"scene_{idx:03d}_subs.mp4")
                self._burn_subtitles(with_audio, srt, with_subs)
                scene_final_videos.append(with_subs)
            else:
                scene_final_videos.append(with_audio)

        # Step 4: Concatenate all scenes
        safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
        final_path = os.path.join(str(OUTPUT_DIR), f"{safe_title}.mp4")

        if len(scene_final_videos) == 1:
            cmd = [self.ffmpeg, "-y", "-i", scene_final_videos[0], "-c", "copy", final_path]
            self._run(cmd)
        else:
            self._concat_scenes(scene_final_videos, final_path)

        print(f"[ASSY] Final video: {final_path}")
        return final_path

    def add_intro_card(
        self,
        video_path: str,
        title: str,
        subtitle: str = "",
        duration: float = 3.0,
        output_path: str = None,
    ) -> str:
        """
        Add a simple text intro card before the video.
        Uses FFmpeg to generate a black background with centered text.
        """
        if output_path is None:
            output_path = video_path.replace(".mp4", "_intro.mp4")

        # Create intro card
        intro_path = video_path.replace(".mp4", "_card.mp4")
        escaped_title = title.replace("'", "\\'").replace(":", "\\:")
        escaped_sub = subtitle.replace("'", "\\'").replace(":", "\\:")

        drawtext = (
            f"drawtext=text='{escaped_title}':"
            f"fontsize=48:fontcolor=white:"
            f"x=(w-text_w)/2:y=(h-text_h)/2-30:"
            f"box=1:boxcolor=black@0.5:boxborderw=10"
        )
        if subtitle:
            drawtext += (
                f",drawtext=text='{escaped_sub}':"
                f"fontsize=28:fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2+30"
            )

        cmd = [
            self.ffmpeg, "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s=512x512:d={duration}",
            "-vf", drawtext,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(VIDEO_FPS),
            intro_path,
        ]
        self._run(cmd)

        # Concat intro + main video
        list_file = intro_path + ".txt"
        with open(list_file, "w") as f:
            f.write(f"file '{os.path.abspath(intro_path)}'\n")
            f.write(f"file '{os.path.abspath(video_path)}'\n")

        cmd = [
            self.ffmpeg, "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_path,
        ]
        self._run(cmd)
        return output_path
