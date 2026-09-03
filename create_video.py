"""
AI Video Creator — Complete pipeline that runs on GitHub Actions.
NO GPU needed. NO local installation needed. NO computer needed.

How it works:
1. Story is generated using Ollama API (via GitHub Actions)
2. Voice-over is generated using gTTS (Google Translate TTS) — supports Bengali & Hindi
3. Images are generated using Pollinations.ai (free AI image generation API)
4. Video is assembled using FFmpeg with Ken Burns effect (zoom/pan)
5. Subtitles are generated using whisper (small model)
6. Final MP4 is uploaded as a GitHub Actions artifact for download

Usage on GitHub:
- Go to Actions tab → "Create AI Video" → Run workflow
- Enter your topic, language (bn/hi), and length (short/long)
- Wait ~10-15 minutes
- Download the video from the Artifacts section
"""

import os
import sys
import json
import time
import subprocess
import requests
import urllib.parse

# ── Configuration ───────────────────────────────────────────────────
TOPIC = os.environ.get("VIDEO_TOPIC", "সুন্দরবনের বাঘ")
LANGUAGE = os.environ.get("VIDEO_LANGUAGE", "bn")  # bn or hi
LENGTH = os.environ.get("VIDEO_LENGTH", "short")    # short or long

# Use environment variables or fall back to direct values
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
STORY_MODEL = os.environ.get("STORY_MODEL", "qwen2.5:3b")

OUTPUT_DIR = "/tmp/output"
TEMP_DIR = "/tmp/work"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


def run(cmd):
    """Run shell command."""
    print(f"  $ {' '.join(cmd[:5])}...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ERROR: {r.stderr[:300]}")
    return r


def get_duration(path):
    """Get media duration in seconds."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def fmt_srt_time(seconds):
    """Format time for SRT subtitles."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ════════════════════════════════════════════════════════════════════
# STEP 1: Story Generation (using Ollama or fallback to built-in stories)
# ════════════════════════════════════════════════════════════════════

def generate_story_ollama(topic, language, num_scenes):
    """Generate story using Ollama."""
    if language == "hi":
        sys_prompt = f"""तुम एक पेशेवर वीडियो स्क्रिप्ट लेखक हो।
उपयोगकर्ता एक टॉपिक देगा। तुम्हें उस टॉपिक पर एक जानकारीपूर्ण वीडियो स्क्रिप्ट लिखनी है।
स्क्रिप्ट को {num_scenes} दृश्यों में बांटो। हर दृश्य के लिए दो:
narration (हिंदी में वॉयस-ओवर टेक्स्ट), visual_prompt (अंग्रेजी में), emotion।
केवल JSON में उत्तर दो: {{"title": "...", "scenes": [{{"narration": "...", "visual_prompt": "...", "emotion": "..."}}]}}"""
        user_msg = f"टॉपिक: {topic}"
    else:
        sys_prompt = f"""তুমি একজন পেশাদার ভিডিও স্ক্রিপ্ট লেখক।
ব্যবহারকারী একটি টপিক দেবে। তোমাকে সেই টপিকে একটি তথ্যবহুল ভিডিও স্ক্রিপ্ট লিখতে হবে।
স্ক্রিপ্টটি {num_scenes}টি দৃশ্যে ভাগ করো। প্রতিটি দৃশ্যের জন্য দাও:
narration (বাংলায় ভয়েস-ওভার টেক্সট), visual_prompt (ইংরেজিতে), emotion।
শুধু JSON এ উত্তর দাও: {{"title": "...", "scenes": [{{"narration": "...", "visual_prompt": "...", "emotion": "..."}}]}}"""
        user_msg = f"টপিক: {topic}"

    try:
        resp = requests.post(f"{OLLAMA_HOST}/api/chat", json={
            "model": STORY_MODEL,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_msg}
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.8}
        }, timeout=120)
        resp.raise_for_status()
        story = json.loads(resp.json()["message"]["content"])
        story["language"] = language
        return story
    except Exception as e:
        print(f"  Ollama failed: {e}")
        print("  Using fallback story generator...")
        return generate_story_fallback(topic, language, num_scenes)


def generate_story_fallback(topic, language, num_scenes):
    """
    Fallback story generator (no Ollama needed).
    Uses a simple template-based approach.
    """
    if language == "hi":
        scenes = [
            {"narration": f"आज हम बात करेंगे {topic} के बारे में। यह एक बहुत ही रोचक विषय है।",
             "visual_prompt": f"cinematic establishing shot related to {topic}, beautiful landscape, golden hour, documentary style",
             "emotion": "neutral"},
            {"narration": f"{topic} का इतिहास बहुत पुराना है। इसकी शुरुआत सदियों पहले हुई थी।",
             "visual_prompt": f"historical scene related to {topic}, ancient architecture, warm colors, cinematic",
             "emotion": "calm"},
            {"narration": f"आज के समय में {topic} का महत्व और भी बढ़ गया है।",
             "visual_prompt": f"modern scene related to {topic}, contemporary setting, bright daylight, documentary",
             "emotion": "excited"},
            {"narration": f"{topic} से जुड़े कई रोचक तथ्य हैं जो हमें आश्चर्यचकित करते हैं।",
             "visual_prompt": f"close-up details related to {topic}, macro photography, cinematic lighting",
             "emotion": "dramatic"},
            {"narration": f"भविष्य में {topic} का और भी विकास होगा।",
             "visual_prompt": f"futuristic scene related to {topic}, modern technology, blue tones, cinematic",
             "emotion": "excited"},
            {"narration": f"आशा है आपको {topic} के बारे में यह जानकारी उपयोगी लगी होगी। धन्यवाद!",
             "visual_prompt": f"beautiful closing shot related to {topic}, sunset, cinematic, peaceful",
             "emotion": "happy"},
        ]
        title = f"{topic} के बारे में"
    else:
        scenes = [
            {"narration": f"আজ আমরা কথা বলবো {topic} সম্পর্কে। এটি একটি অত্যন্ত আকর্ষণীয় বিষয়।",
             "visual_prompt": f"cinematic establishing shot related to {topic}, beautiful landscape, golden hour, documentary style",
             "emotion": "neutral"},
            {"narration": f"{topic}-এর ইতিহাস অনেক পুরোনো। এর সূচনা শত শত বছর আগে।",
             "visual_prompt": f"historical scene related to {topic}, ancient architecture, warm colors, cinematic",
             "emotion": "calm"},
            {"narration": f"বর্তমান সময়ে {topic}-এর গুরুত্ব আরও বেড়ে গেছে।",
             "visual_prompt": f"modern scene related to {topic}, contemporary setting, bright daylight, documentary",
             "emotion": "excited"},
            {"narration": f"{topic} সম্পর্কে অনেক চমৎকার তথ্য রয়েছে যা আমাদের অবাক করে।",
             "visual_prompt": f"close-up details related to {topic}, macro photography, cinematic lighting",
             "emotion": "dramatic"},
            {"narration": f"ভবিষ্যতে {topic}-এর আরও উন্নতি হবে।",
             "visual_prompt": f"futuristic scene related to {topic}, modern technology, blue tones, cinematic",
             "emotion": "excited"},
            {"narration": f"আশা করি {topic} সম্পর্কে এই তথ্য আপনার কাজে লেগেছে। ধন্যবাদ!",
             "visual_prompt": f"beautiful closing shot related to {topic}, sunset, cinematic, peaceful",
             "emotion": "happy"},
        ]
        title = f"{topic} সম্পর্কে"

    story = {
        "title": title,
        "language": language,
        "scenes": scenes[:num_scenes],
    }
    return story


# ════════════════════════════════════════════════════════════════════
# STEP 2: Voice-Over Generation (using gTTS — Google Translate TTS)
# ════════════════════════════════════════════════════════════════════

def generate_voiceover(scenes, language):
    """Generate voice-over using gTTS (Google Translate TTS). Free, no API key."""
    from gtts import gTTS
    import soundfile as sf
    import numpy as np

    audio_dir = os.path.join(TEMP_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    voice_results = []
    for i, scene in enumerate(scenes):
        print(f"  🎤 দৃশ্য {i+1}/{len(scenes)} ভয়েস তৈরি হচ্ছে...")
        text = scene["narration"]
        tts = gTTS(text=text, lang=language, slow=False)
        mp3_path = os.path.join(audio_dir, f"scene_{i:03d}.mp3")
        tts.save(mp3_path)

        # Convert MP3 to WAV
        wav_path = os.path.join(audio_dir, f"scene_{i:03d}.wav")
        run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1", wav_path])

        duration = get_duration(wav_path)
        voice_results.append({
            "scene_index": i,
            "audio_path": wav_path,
            "duration": duration,
        })
        print(f"     ✅ {duration:.1f}s")

    return voice_results


# ════════════════════════════════════════════════════════════════════
# STEP 3: Subtitle Generation (using whisper)
# ════════════════════════════════════════════════════════════════════

def generate_subtitles(voice_results, language):
    """Generate SRT subtitles from audio using whisper."""
    import whisper

    print("  📝 Whisper লোড হচ্ছে...")
    model = whisper.load_model("base")
    print("  ✅ প্রস্তুত!")

    sub_dir = os.path.join(TEMP_DIR, "subs")
    os.makedirs(sub_dir, exist_ok=True)
    subtitle_results = []

    for vr in voice_results:
        print(f"  📝 দৃশ্য {vr['scene_index']+1} সাবটাইটেল...")
        result = model.transcribe(vr["audio_path"], language=language, verbose=False)
        srt_path = os.path.join(sub_dir, f"scene_{vr['scene_index']:03d}.srt")

        with open(srt_path, "w", encoding="utf-8") as f:
            for j, seg in enumerate(result["segments"], 1):
                f.write(f"{j}\n")
                f.write(f"{fmt_srt_time(seg['start'])} --> {fmt_srt_time(seg['end'])}\n")
                f.write(f"{seg['text'].strip()}\n\n")

        subtitle_results.append({
            "scene_index": vr["scene_index"],
            "srt_path": srt_path,
        })

    return subtitle_results


# ════════════════════════════════════════════════════════════════════
# STEP 4: Image Generation (using Pollinations.ai — free, no API key)
# ════════════════════════════════════════════════════════════════════

def generate_images(scenes):
    """Generate images using Pollinations.ai free API."""
    img_dir = os.path.join(TEMP_DIR, "images")
    os.makedirs(img_dir, exist_ok=True)
    image_results = []

    for i, scene in enumerate(scenes):
        prompt = scene["visual_prompt"]
        # Add cinematic style
        full_prompt = f"{prompt}, cinematic, dramatic lighting, highly detailed, 8k, professional photography"
        # URL encode the prompt
        encoded = urllib.parse.quote(full_prompt)
        # Pollinations.ai URL
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&nologo=true&seed={42+i}"

        img_path = os.path.join(img_dir, f"scene_{i:03d}.jpg")
        print(f"  🖼️ দৃশ্য {i+1}/{len(scenes)} ছবি তৈরি হচ্ছে...")

        try:
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()
            with open(img_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"     ✅ সেভ হয়েছে")
            image_results.append({"scene_index": i, "image_path": img_path})
        except Exception as e:
            print(f"     ❌ ত্রুটি: {e}")
            # Create a black placeholder image
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1024x576:d=1", "-frames:v", "1", img_path])
            image_results.append({"scene_index": i, "image_path": img_path})

    return image_results


# ════════════════════════════════════════════════════════════════════
# STEP 5: Video Assembly with Ken Burns Effect
# ════════════════════════════════════════════════════════════════════

def assemble_video(scenes, voice_results, subtitle_results, image_results, title):
    """Assemble final video from images, audio, and subtitles."""
    final_dir = os.path.join(TEMP_DIR, "final")
    os.makedirs(final_dir, exist_ok=True)
    scene_videos = []

    for vr in voice_results:
        idx = vr["scene_index"]
        audio_path = vr["audio_path"]
        audio_dur = vr["duration"]
        srt_path = subtitle_results[idx]["srt_path"]
        img_path = image_results[idx]["image_path"]

        # Create video from image with Ken Burns zoom effect
        # Zoom in slowly for cinematic feel
        scene_video = os.path.join(final_dir, f"scene_{idx:03d}_video.mp4")
        vf = (
            f"scale=1200:675:force_original_aspect_ratio=increase,"
            f"crop=1024:576,"
            f"zoompan=z='min(zoom+0.0008,1.15)':d={int(audio_dur*25)}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1024x576:fps=25"
        )
        run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", img_path,
            "-i", audio_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(audio_dur),
            "-shortest",
            scene_video,
        ])

        # Burn subtitles
        with_subs = os.path.join(final_dir, f"scene_{idx:03d}_final.mp4")
        srt_escaped = srt_path.replace("'", "\\'")
        run([
            "ffmpeg", "-y", "-i", scene_video,
            "-vf", f"subtitles='{srt_escaped}':force_style='FontName=Noto Sans,FontSize=6,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=20'",
            "-c:v", "libx264", "-crf", "20", "-c:a", "copy", "-pix_fmt", "yuv420p",
            with_subs,
        ])
        scene_videos.append(with_subs)

    # Concatenate all scenes
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:50]
    final_path = os.path.join(OUTPUT_DIR, f"{safe_title}.mp4")

    list_file = os.path.join(final_dir, "concat_list.txt")
    with open(list_file, "w") as f:
        for sv in scene_videos:
            f.write(f"file '{sv}'\n")

    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", final_path])

    return final_path


# ════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print(f"🎬 AI Video Creator")
    print(f"   টপিক: {TOPIC}")
    print(f"   ভাষা: {LANGUAGE}")
    print(f"   দৈর্ঘ্য: {LENGTH}")
    print("=" * 60)

    num_scenes = 3 if LENGTH == "short" else 6

    # Step 1: Story
    print("\n📝 ধাপ ১: স্টোরি তৈরি হচ্ছে...")
    story = generate_story_ollama(TOPIC, LANGUAGE, num_scenes)
    print(f"  🎬 শিরোনাম: {story['title']}")
    print(f"  📊 দৃশ্য সংখ্যা: {len(story['scenes'])}")
    for i, scene in enumerate(story['scenes']):
        print(f"  --- দৃশ্য {i+1} ---")
        print(f"  ন্যারেশন: {scene['narration'][:60]}...")
        print(f"  ভিজ্যুয়াল: {scene['visual_prompt'][:60]}...")

    # Step 2: Voice-over
    print("\n🎤 ধাপ ২: ভয়েস-ওভার তৈরি হচ্ছে...")
    voice_results = generate_voiceover(story['scenes'], LANGUAGE)
    print(f"  ✅ {len(voice_results)} টি ভয়েস প্রস্তুত")

    # Step 3: Subtitles
    print("\n📝 ধাপ ৩: সাবটাইটেল তৈরি হচ্ছে...")
    subtitle_results = generate_subtitles(voice_results, LANGUAGE)
    print(f"  ✅ সাবটাইটেল প্রস্তুত")

    # Step 4: Images
    print("\n🖼️ ধাপ ৪: AI ছবি তৈরি হচ্ছে...")
    image_results = generate_images(story['scenes'])
    print(f"  ✅ {len(image_results)} টি ছবি প্রস্তুত")

    # Step 5: Video Assembly
    print("\n🎬 ধাপ ৫: ফাইনাল ভিডিও তৈরি হচ্ছে...")
    final_path = assemble_video(
        story['scenes'], voice_results, subtitle_results,
        image_results, story['title']
    )

    size_mb = os.path.getsize(final_path) / 1024 / 1024
    print(f"\n{'=' * 60}")
    print(f"✅ ফাইনাল ভিডিও প্রস্তুত!")
    print(f"   📁 ফাইল: {final_path}")
    print(f"   📏 সাইজ: {size_mb:.1f} MB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
