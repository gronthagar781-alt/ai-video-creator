"""
Lightweight AI Video Creator — runs on Hugging Face Spaces (free CPU).
Public URL: https://huggingface.co/spaces/<username>/ai-video-creator

No GPU needed. No model downloads. Uses free APIs:
- gTTS for voice-over (Bengali & Hindi)
- Pollinations.ai for AI images
- FFmpeg for video assembly
- Simple story templates (no Ollama needed)
"""

import os
import json
import time
import subprocess
import tempfile
import urllib.parse
import requests

import gradio as gr
from gtts import gTTS


# ── Helper functions ─────────────────────────────────────────────────

def run(cmd):
    """Run shell command."""
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"CMD ERROR: {r.stderr[:300]}")
    return r


def get_duration(path):
    """Get media duration in seconds."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        return 5.0


def fmt_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ── Story Templates ─────────────────────────────────────────────────

def generate_story(topic, language, length):
    """Generate a story using built-in templates."""
    num_scenes = 3 if length == "short" else 6

    if language == "hi":
        scenes = [
            {"narration": f"आज हम बात करेंगे {topic} के बारे में। यह एक बहुत ही रोचक और महत्वपूर्ण विषय है।",
             "visual_prompt": f"cinematic wide shot of {topic}, beautiful landscape, golden hour lighting, documentary photography, highly detailed",
             "emotion": "neutral"},
            {"narration": f"{topic} का इतिहास बहुत पुराना है। इसकी शुरुआत सदियों पहले हुई थी, और तब से यह हमारी संस्कृति का हिस्सा बन गया।",
             "visual_prompt": f"historical scene of {topic}, ancient architecture, warm vintage colors, cinematic composition, film still",
             "emotion": "calm"},
            {"narration": f"{topic} से जुड़े कई रोचक तथ्य हैं जो हमें आश्चर्यचकित करते हैं और हमारी जानकारी बढ़ाते हैं।",
             "visual_prompt": f"detailed close-up of {topic}, macro photography, dramatic lighting, shallow depth of field, cinematic",
             "emotion": "excited"},
            {"narration": f"आज के समय में {topic} का महत्व और भी बढ़ गया है। आधुनिक तकनीक ने इसे नया रूप दिया है।",
             "visual_prompt": f"modern scene of {topic}, contemporary technology, bright daylight, documentary style, 4k",
             "emotion": "excited"},
            {"narration": f"भविष्य में {topic} का और भी विकास होगा, और यह हमारे जीवन में और भी महत्वपूर्ण भूमिका निभाएगा।",
             "visual_prompt": f"futuristic vision of {topic}, modern technology, blue tones, sci-fi aesthetic, cinematic",
             "emotion": "dramatic"},
            {"narration": f"आशा है आपको {topic} के बारे में यह जानकारी उपयोगी लगी होगी। धन्यवाद, और अगली बार तक सुरक्षित रहें!",
             "visual_prompt": f"beautiful closing shot of {topic}, sunset, peaceful, cinematic, warm golden light",
             "emotion": "happy"},
        ]
        title = f"{topic} के बारे में"
    else:
        scenes = [
            {"narration": f"আজ আমরা কথা বলবো {topic} সম্পর্কে। এটি একটি অত্যন্ত আকর্ষণীয় এবং গুরুত্বপূর্ণ বিষয়।",
             "visual_prompt": f"cinematic wide shot of {topic}, beautiful landscape, golden hour lighting, documentary photography, highly detailed",
             "emotion": "neutral"},
            {"narration": f"{topic}-এর ইতিহাস অনেক পুরোনো। এর সূচনা শত শত বছর আগে, এবং তখন থেকেই এটি আমাদের সংস্কৃতির অংশ।",
             "visual_prompt": f"historical scene of {topic}, ancient architecture, warm vintage colors, cinematic composition, film still",
             "emotion": "calm"},
            {"narration": f"{topic} সম্পর্কে অনেক চমৎকার তথ্য রয়েছে যা আমাদের অবাক করে এবং জ্ঞান বৃদ্ধি করে।",
             "visual_prompt": f"detailed close-up of {topic}, macro photography, dramatic lighting, shallow depth of field, cinematic",
             "emotion": "excited"},
            {"narration": f"বর্তমান সময়ে {topic}-এর গুরুত্ব আরও বেড়ে গেছে। আধুনিক প্রযুক্তি একে নতুন রূপ দিয়েছে।",
             "visual_prompt": f"modern scene of {topic}, contemporary technology, bright daylight, documentary style, 4k",
             "emotion": "excited"},
            {"narration": f"ভবিষ্যতে {topic}-এর আরও উন্নতি হবে, এবং এটি আমাদের জীবনে আরও গুরুত্বপূর্ণ ভূমিকা নেবে।",
             "visual_prompt": f"futuristic vision of {topic}, modern technology, blue tones, sci-fi aesthetic, cinematic",
             "emotion": "dramatic"},
            {"narration": f"আশা করি {topic} সম্পর্কে এই তথ্য আপনার কাজে লেগেছে। ধন্যবাদ, আবার দেখা হবে!",
             "visual_prompt": f"beautiful closing shot of {topic}, sunset, peaceful, cinematic, warm golden light",
             "emotion": "happy"},
        ]
        title = f"{topic} সম্পর্কে"

    return {"title": title, "language": language, "scenes": scenes[:num_scenes]}


# ── Voice Generation ────────────────────────────────────────────────

def generate_voice(scenes, language, work_dir):
    """Generate voice-over using gTTS."""
    audio_dir = os.path.join(work_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    results = []

    for i, scene in enumerate(scenes):
        tts = gTTS(text=scene["narration"], lang=language, slow=False)
        mp3_path = os.path.join(audio_dir, f"scene_{i:03d}.mp3")
        tts.save(mp3_path)

        wav_path = os.path.join(audio_dir, f"scene_{i:03d}.wav")
        run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1", wav_path])

        dur = get_duration(wav_path)
        results.append({"scene_index": i, "audio_path": wav_path, "duration": dur,
                        "text": scene["narration"], "emotion": scene.get("emotion", "neutral")})

    return results


# ── Image Generation ────────────────────────────────────────────────

def generate_images(scenes, work_dir):
    """Generate images using Pollinations.ai free API."""
    img_dir = os.path.join(work_dir, "images")
    os.makedirs(img_dir, exist_ok=True)
    results = []

    for i, scene in enumerate(scenes):
        prompt = f"{scene['visual_prompt']}, cinematic, dramatic lighting, highly detailed, 8k, professional photography"
        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&nologo=true&seed={42+i}"

        img_path = os.path.join(img_dir, f"scene_{i:03d}.jpg")
        try:
            resp = requests.get(url, timeout=90, stream=True)
            resp.raise_for_status()
            with open(img_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            print(f"Image {i} failed: {e}")
            run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                 f"color=c=0x1a1a2e:s=1024x576:d=1", "-frames:v", "1", img_path])

        results.append({"scene_index": i, "image_path": img_path})

    return results


# ── Subtitle Generation ────────────────────────────────────────────

def generate_subtitles(voice_results, work_dir):
    """Generate SRT subtitles from known narration text."""
    sub_dir = os.path.join(work_dir, "subs")
    os.makedirs(sub_dir, exist_ok=True)
    results = []

    for vr in voice_results:
        idx = vr["scene_index"]
        srt_path = os.path.join(sub_dir, f"scene_{idx:03d}.srt")

        text = vr["text"]
        dur = vr["duration"]
        import re
        sentences = re.split(r'[।.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            sentences = [text]

        seg_dur = dur / len(sentences)

        with open(srt_path, "w", encoding="utf-8") as f:
            for j, sent in enumerate(sentences):
                start = j * seg_dur
                end = (j + 1) * seg_dur
                f.write(f"{j+1}\n")
                f.write(f"{fmt_srt_time(start)} --> {fmt_srt_time(end)}\n")
                f.write(f"{sent}\n\n")

        results.append({"scene_index": idx, "srt_path": srt_path})

    return results


# ── Video Assembly ─────────────────────────────────────────────────

def assemble_video(voice_results, subtitle_results, image_results, title, work_dir):
    """Assemble final video with Ken Burns zoom effect."""
    final_dir = os.path.join(work_dir, "final")
    os.makedirs(final_dir, exist_ok=True)
    scene_videos = []

    for vr in voice_results:
        idx = vr["scene_index"]
        audio_path = vr["audio_path"]
        audio_dur = vr["duration"]
        srt_path = subtitle_results[idx]["srt_path"]
        img_path = image_results[idx]["image_path"]

        scene_video = os.path.join(final_dir, f"scene_{idx:03d}.mp4")
        fps = 25
        total_frames = int(audio_dur * fps)

        vf = (
            f"scale=1200:675:force_original_aspect_ratio=increase,"
            f"crop=1024:576,"
            f"zoompan=z='min(zoom+0.0008,1.15)':d={total_frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1024x576:fps={fps}"
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

        with_subs = os.path.join(final_dir, f"scene_{idx:03d}_sub.mp4")
        srt_escaped = srt_path.replace("'", "\\'")
        run([
            "ffmpeg", "-y", "-i", scene_video,
            "-vf", f"subtitles='{srt_escaped}':force_style='FontName=Noto Sans,FontSize=6,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=20'",
            "-c:v", "libx264", "-crf", "20", "-c:a", "copy", "-pix_fmt", "yuv420p",
            with_subs,
        ])
        scene_videos.append(with_subs)

    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:50]
    final_path = os.path.join(work_dir, f"{safe_title}.mp4")

    list_file = os.path.join(final_dir, "concat.txt")
    with open(list_file, "w") as f:
        for sv in scene_videos:
            f.write(f"file '{sv}'\n")

    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", final_path])

    return final_path


# ── Main Pipeline ───────────────────────────────────────────────────

def create_video(topic, language, length, progress=gr.Progress()):
    """Full video creation pipeline."""
    work_dir = tempfile.mkdtemp(prefix="video_")

    progress(0.1, desc="স্টোরি তৈরি হচ্ছে...")
    story = generate_story(topic, language, length)

    story_text = f"শিরোনাম: {story['title']}\nদৃশ্য সংখ্যা: {len(story['scenes'])}\n\n"
    for i, scene in enumerate(story['scenes']):
        story_text += f"--- দৃশ্য {i+1} ({scene.get('emotion','')}) ---\n"
        story_text += f"ন্যারেশন: {scene['narration']}\n\n"

    progress(0.25, desc="ভয়েস-ওভার তৈরি হচ্ছে...")
    voice_results = generate_voice(story['scenes'], language, work_dir)

    progress(0.45, desc="AI ছবি তৈরি হচ্ছে...")
    image_results = generate_images(story['scenes'], work_dir)

    progress(0.65, desc="সাবটাইটেল তৈরি হচ্ছে...")
    subtitle_results = generate_subtitles(voice_results, work_dir)

    progress(0.80, desc="ভিডিও তৈরি হচ্ছে...")
    final_path = assemble_video(voice_results, subtitle_results, image_results,
                                story['title'], work_dir)

    progress(1.0, desc="সম্পূর্ণ!")
    return final_path, story_text


# ── Gradio UI ──────────────────────────────────────────────────────

with gr.Blocks(
    title="AI Video Creator",
    theme=gr.themes.Soft(primary_hue="red", secondary_hue="pink"),
) as app:

    gr.Markdown("""
    # AI Video Creator — বাংলা ও हिन्दी

    শুধু একটি টপিক দিন — AI স্টোরি, ভয়েস-ওভার, সাবটাইটেল ও সিনেমাটিক ভিডিও তৈরি করবে।

    সম্পূর্ণ ফ্রি। কোনো সাইন-আপ নেই। কোনো API কী নেই।
    """)

    with gr.Row():
        topic_input = gr.Textbox(
            label="টপিক (Topic)",
            placeholder="যেমন: সুন্দরবনের বাঘ / ताजमहल / গঙ্গা নদী",
            lines=2,
            scale=3,
        )

    with gr.Row():
        lang_input = gr.Dropdown(
            choices=[("বাংলা (Bengali)", "bn"), ("हिन्दी (Hindi)", "hi")],
            value="bn",
            label="ভাষা (Language)",
            scale=1,
        )
        length_input = gr.Dropdown(
            choices=[("শর্ট (~30s)", "short"), ("ফুল লেন্থ (~60s)", "long")],
            value="short",
            label="দৈর্ঘ্য (Length)",
            scale=1,
        )

    create_btn = gr.Button("ভিডিও তৈরি করুন", variant="primary", size="lg")

    story_output = gr.Textbox(label="স্টোরি", lines=10, interactive=False)
    video_output = gr.Video(label="আপনার ভিডিও")

    create_btn.click(
        fn=create_video,
        inputs=[topic_input, lang_input, length_input],
        outputs=[video_output, story_output],
    )

    gr.Markdown("""
    ---
    প্রযুক্তি: gTTS (ভয়েস) · Pollinations.ai (AI ছবি) · FFmpeg (ভিডিও) · Gradio (UI)

    ভিডিও তৈরি হতে ২-৫ মিনিট সময় লাগবে। ধৈর্য ধরুন।
    """)


if __name__ == "__main__":
    app.launch()
