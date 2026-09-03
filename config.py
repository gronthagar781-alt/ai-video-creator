"""
Central configuration for the AI Video Creator.
All paths and model settings live here so you can tweak without touching the app logic.
"""

import os
from pathlib import Path

# ── Base directories ────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"

for d in (DATA_DIR, OUTPUT_DIR, TEMP_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Ollama (Story Generation) ────────────────────────────────────────
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# Models that work well for Bengali & Hindi creative writing.
# Pull with:  ollama pull qwen2.5:7b
STORY_MODEL_BN = os.getenv("STORY_MODEL_BN", "qwen2.5:7b")   # Bengali
STORY_MODEL_HI = os.getenv("STORY_MODEL_HI", "qwen2.5:7b")   # Hindi

# ── TTS (IndicF5 by AI4Bharat) ──────────────────────────────────────
TTS_MODEL_ID = "ai4bharat/IndicF5"
TTS_SAMPLE_RATE = 24000
# Reference voice prompts directory — drop 5-12 s WAV clips here.
# Each file becomes a selectable voice.
VOICE_PROMPTS_DIR = DATA_DIR / "voice_prompts"
VOICE_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

# Built-in reference prompt names (shipped with IndicF5)
DEFAULT_VOICES = {
    "bn_female": {"lang": "bn", "gender": "female", "desc": "বাংলা নারী কণ্ঠ"},
    "bn_male":   {"lang": "bn", "gender": "male",   "desc": "বাংলা পুরুষ কণ্ঠ"},
    "hi_female": {"lang": "hi", "gender": "female", "desc": "হিন্দি নারী কণ্ঠ"},
    "hi_male":   {"lang": "hi", "gender": "male",   "desc": "হিন্দি পুরুষ কণ্ঠ"},
}

# ── Video Generation (AnimateDiff via Diffusers) ────────────────────
VIDEO_MODEL = "runwayml/stable-diffusion-v1-5"
MOTION_ADAPTER = "guoyww/animatediff-motion-module-v1-5-2"
VIDEO_WIDTH = 512
VIDEO_HEIGHT = 512
VIDEO_FPS = 8
VIDEO_FRAMES_SHORT = 16      # ~2 s at 8 fps
VIDEO_FRAMES_LONG = 32        # ~4 s at 8 fps — multiple clips concatenated for full-length
VIDEO_NUM_INFERENCE_STEPS = 25
VIDEO_GUIDANCE_SCALE = 7.5

# ── Subtitles (Whisper) ─────────────────────────────────────────────
WHISPER_MODEL = "base"        # tiny | base | small | medium | large
WHISPER_LANGUAGE = None       # auto-detect; or "bn" / "hi"

# ── FFmpeg ──────────────────────────────────────────────────────────
FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")
FFPROBE_BINARY = os.getenv("FFPROBE_BINARY", "ffprobe")

# ── Flask ────────────────────────────────────────────────────────────
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
