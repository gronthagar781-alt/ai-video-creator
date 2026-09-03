"""
Video generation module — uses AnimateDiff + Stable Diffusion (via HuggingFace
Diffusers) to create cinematic AI video clips from text prompts.

Supports both realistic and animation styles. Each scene's visual_prompt
becomes a short video clip. Clips are then concatenated to match the
voice-over duration.
"""

import os
from pathlib import Path
from config import (
    VIDEO_MODEL, MOTION_ADAPTER,
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
    VIDEO_FRAMES_SHORT, VIDEO_FRAMES_LONG,
    VIDEO_NUM_INFERENCE_STEPS, VIDEO_GUIDANCE_SCALE,
    TEMP_DIR,
)


class VideoGenerator:
    """Generates AI video clips from text prompts using AnimateDiff."""

    _pipe = None  # lazy-loaded singleton

    # Style presets applied as prompt suffixes
    STYLE_PRESETS = {
        "cinematic": "cinematic shot, dramatic lighting, film grain, 35mm, "
                     "shallow depth of field, highly detailed, 8k",
        "realistic": "photorealistic, natural lighting, documentary style, "
                     "highly detailed, 4k, sharp focus",
        "animation": "stylized animation, vibrant colors, studio anime style, "
                     "detailed background, smooth shading",
        "fantasy":   "epic fantasy art, magical atmosphere, ethereal lighting, "
                     "intricate details, digital painting",
        "documentary": "nature documentary style, wide establishing shot, "
                       "natural colors, cinematic, National Geographic style",
    }

    def __init__(self, style: str = "cinematic"):
        self.style = style

    def _load_pipeline(self):
        """Load the AnimateDiff pipeline (downloads on first run)."""
        if VideoGenerator._pipe is not None:
            return VideoGenerator._pipe

        import torch
        from diffusers import (
            AnimateDiffPipeline,
            MotionAdapter,
            DDIMScheduler,
        )

        print("[VIDEO] Loading AnimateDiff pipeline...")

        # Load motion adapter
        adapter = MotionAdapter.from_pretrained(MOTION_ADAPTER)
        if torch.cuda.is_available():
            adapter = adapter.to("cuda")

        # Load pipeline with SD 1.5 base
        pipe = AnimateDiffPipeline.from_pretrained(
            VIDEO_MODEL,
            motion_adapter=adapter,
            torch_dtype=torch.float16,
        )
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")

        # Optimise memory
        pipe.enable_vae_slicing()
        pipe.enable_model_cpu_offload()

        # Scheduler — linear beta schedule recommended for AnimateDiff
        pipe.scheduler = DDIMScheduler.from_config(
            pipe.scheduler.config,
            beta_schedule="linear",
            clip_sample=False,
        )

        VideoGenerator._pipe = pipe
        print("[VIDEO] Pipeline ready.")
        return pipe

    def generate_clip(
        self,
        prompt: str,
        output_path: str = None,
        num_frames: int = None,
        negative_prompt: str = None,
        seed: int = None,
    ) -> str:
        """
        Generate a single video clip from a text prompt.

        Args:
            prompt:        Text description of the scene.
            output_path:   Where to save the MP4.
            num_frames:    Number of frames (default VIDEO_FRAMES_SHORT).
            negative_prompt: What to avoid in the generation.
            seed:          Random seed for reproducibility.

        Returns:
            Path to the generated MP4 file.
        """
        import torch
        from diffusers.utils import export_to_video

        pipe = self._load_pipeline()

        if num_frames is None:
            num_frames = VIDEO_FRAMES_SHORT

        # Apply style preset
        style_suffix = self.STYLE_PRESETS.get(self.style, self.STYLE_PRESETS["cinematic"])
        full_prompt = f"{prompt}, {style_suffix}"

        if negative_prompt is None:
            negative_prompt = (
                "low quality, blurry, distorted, watermark, text, "
                "deformed, ugly, bad anatomy, extra limbs"
            )

        if seed is not None:
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
            generator = generator.manual_seed(seed)
        else:
            generator = None

        print(f"[VIDEO] Generating {num_frames} frames for: {prompt[:60]}...")

        frames = pipe(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            num_frames=num_frames,
            num_inference_steps=VIDEO_NUM_INFERENCE_STEPS,
            guidance_scale=VIDEO_GUIDANCE_SCALE,
            generator=generator,
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
        ).frames[0]

        if output_path is None:
            output_path = str(TEMP_DIR / "clip.mp4")

        export_to_video(frames, output_path, fps=VIDEO_FPS)
        print(f"[VIDEO] Saved: {output_path}")
        return output_path

    def generate_for_scenes(
        self,
        scenes: list,
        voice_durations: list = None,
        output_dir: str = None,
        style: str = None,
    ) -> list:
        """
        Generate video clips for all scenes in a story.

        Args:
            scenes:          List of scene dicts with 'visual_prompt'.
            voice_durations:  List of {"scene_index", "duration"} dicts.
                              Used to determine how many clips to generate
                              per scene (to fill the voice-over time).
            output_dir:       Directory to save clips.
            style:            Override the style preset.

        Returns:
            List of {"scene_index", "clip_paths": [str], "total_duration": float}.
        """
        if style:
            self.style = style

        if output_dir is None:
            output_dir = str(TEMP_DIR / "video_clips")
        os.makedirs(output_dir, exist_ok=True)

        # Build duration lookup
        dur_map = {}
        if voice_durations:
            for d in voice_durations:
                dur_map[d["scene_index"]] = d["duration"]

        results = []
        for i, scene in enumerate(scenes):
            prompt = scene["visual_prompt"]
            target_dur = dur_map.get(i, 4.0)  # default 4s

            # Each clip is ~2s (16 frames / 8 fps). Generate enough to fill.
            clips_per_scene = max(1, int(target_dur / 2.0) + 1)
            clip_paths = []

            # Vary the prompt slightly for each clip to create variety
            for j in range(clips_per_scene):
                varied_prompt = prompt
                if j > 0:
                    varied_prompt = f"{prompt}, continuation, different angle"

                clip_path = os.path.join(output_dir, f"scene_{i:03d}_clip_{j:03d}.mp4")
                self.generate_clip(varied_prompt, clip_path, seed=42 + i * 100 + j)
                clip_paths.append(clip_path)

            results.append({
                "scene_index": i,
                "clip_paths": clip_paths,
                "target_duration": target_dur,
            })

        return results

    def list_styles(self) -> dict:
        """Return available style presets."""
        return self.STYLE_PRESETS


def generate_image_fallback(prompt: str, output_path: str, style: str = "cinematic"):
    """
    Fallback: generate a single static image using Stable Diffusion if
    AnimateDiff is too heavy. Useful for low-VRAM machines.
    """
    import torch
    from diffusers import StableDiffusionPipeline

    style_suffix = VideoGenerator.STYLE_PRESETS.get(style, "")
    full_prompt = f"{prompt}, {style_suffix}"

    pipe = StableDiffusionPipeline.from_pretrained(
        VIDEO_MODEL, torch_dtype=torch.float16
    )
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")

    image = pipe(full_prompt, num_inference_steps=30).images[0]
    image.save(output_path)
    return output_path
