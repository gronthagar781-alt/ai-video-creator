"""
Voice-over module — uses AI4Bharat IndicF5 for high-quality Bengali & Hindi TTS
with multiple voice options and emotion-aware synthesis.

IndicF5 is a near-human TTS model supporting 11 Indian languages.
It uses reference audio prompts for voice cloning, so you can add any voice
by dropping a 5-12 second WAV clip into data/voice_prompts/.
"""

import os
import wave
import numpy as np
from pathlib import Path
from config import TTS_MODEL_ID, TTS_SAMPLE_RATE, VOICE_PROMPTS_DIR, DEFAULT_VOICES


class VoiceOverGenerator:
    """Wraps IndicF5 for multi-voice, multi-language TTS."""

    _model = None  # lazy-loaded singleton

    def __init__(self):
        self.sample_rate = TTS_SAMPLE_RATE

    def _load_model(self):
        """Load IndicF5 model (downloads on first run, ~1.4 GB)."""
        if VoiceOverGenerator._model is not None:
            return VoiceOverGenerator._model

        import torch
        from transformers import AutoModel

        print(f"[TTS] Loading IndicF5 model ({TTS_MODEL_ID})...")
        VoiceOverGenerator._model = AutoModel.from_pretrained(
            TTS_MODEL_ID, trust_remote_code=True
        )
        if torch.cuda.is_available():
            VoiceOverGenerator._model = VoiceOverGenerator._model.cuda()
        print("[TTS] Model loaded.")
        return VoiceOverGenerator._model

    def _get_reference_audio(self, voice_key: str) -> tuple:
        """
        Return (ref_audio_path, ref_text) for the given voice key.
        Uses bundled IndicF5 prompt files, or custom files from voice_prompts/.
        """
        # Check custom user-provided voice prompts
        custom = VOICE_PROMPTS_DIR / f"{voice_key}.wav"
        if custom.exists():
            # Read transcript if a .txt sidecar exists
            txt = VOICE_PROMPTS_DIR / f"{voice_key}.txt"
            if txt.exists():
                ref_text = txt.read_text(encoding="utf-8").strip()
            else:
                ref_text = ""
            return str(custom), ref_text

        # Use IndicF5's built-in reference prompts
        # These ship with the model repository
        ref_map = {
            "bn_female": ("prompts/BEN_F_HAPPY_00001.wav",
                           "পশ্চিমবঙ্গের সুন্দরবনে বাঘের সংখ্যা বৃদ্ধি পেয়েছে।"),
            "bn_male":   ("prompts/BEN_M_NEUTRAL_00001.wav",
                           "আজকের আবহাওয়া বেশ সুন্দর, আকাশ পরিষ্কার।"),
            "hi_female": ("prompts/HIN_F_HAPPY_00001.wav",
                           "भारत की संस्कृति बहुत ही समृद्ध और विविध है।"),
            "hi_male":   ("prompts/HIN_M_NEUTRAL_00001.wav",
                           "आज का मौसम काफी अच्छा है और आसमान साफ है।"),
        }

        if voice_key not in ref_map:
            raise ValueError(f"Unknown voice key: {voice_key}")

        ref_file, ref_text = ref_map[voice_key]
        return ref_file, ref_text

    def generate(
        self,
        text: str,
        language: str,
        voice_key: str = None,
        output_path: str = None,
    ) -> str:
        """
        Generate a voice-over audio file.

        Args:
            text:        Text to synthesize.
            language:   "bn" or "hi".
            voice_key:  Voice key (e.g. "bn_female"). If None, picks default
                        for the language.
            output_path: Where to save the WAV file.

        Returns:
            Path to the generated WAV file.
        """
        if voice_key is None:
            voice_key = f"{language}_female"

        model = self._load_model()
        ref_audio, ref_text = self._get_reference_audio(voice_key)

        import torch
        import soundfile as sf

        # Generate speech
        with torch.no_grad():
            audio = model(
                text,
                ref_audio_path=ref_audio,
                ref_text=ref_text,
            )

        audio = np.array(audio, dtype=np.float32)

        if output_path is None:
            output_path = "tts_output.wav"

        sf.write(output_path, audio, self.sample_rate)
        print(f"[TTS] Saved: {output_path} ({len(audio)/self.sample_rate:.1f}s)")
        return output_path

    def generate_for_scenes(
        self,
        scenes: list,
        language: str,
        voice_key: str = None,
        output_dir: str = None,
    ) -> list:
        """
        Generate voice-over for all scenes in a story.

        Returns list of {"scene_index": int, "audio_path": str, "duration": float}.
        """
        from config import TEMP_DIR

        if output_dir is None:
            output_dir = str(TEMP_DIR)
        os.makedirs(output_dir, exist_ok=True)

        results = []
        for i, scene in enumerate(scenes):
            text = scene["narration"]
            out = os.path.join(output_dir, f"scene_{i:03d}.wav")
            self.generate(text, language, voice_key, out)

            # Get duration
            import soundfile as sf
            data, sr = sf.read(out)
            duration = len(data) / sr

            results.append({
                "scene_index": i,
                "audio_path": out,
                "duration": duration,
                "text": text,
            })

        return results

    def list_voices(self) -> dict:
        """Return available voices (built-in + custom)."""
        voices = dict(DEFAULT_VOICES)

        # Scan custom voice prompts
        for wav in VOICE_PROMPTS_DIR.glob("*.wav"):
            key = wav.stem
            voices[key] = {
                "lang": key.split("_")[0] if "_" in key else "bn",
                "gender": key.split("_")[1] if "_" in key else "female",
                "desc": f"কাস্টম ভয়েস ({key})",
                "custom": True,
            }

        return voices


# Convenience function for simple usage
def generate_voiceover(
    text: str, language: str, voice_key: str = None, output_path: str = None
) -> str:
    """One-shot TTS call."""
    gen = VoiceOverGenerator()
    return gen.generate(text, language, voice_key, output_path)
