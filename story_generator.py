"""
Story generation module — uses Ollama (local LLM) to create narrated video scripts
in Bengali or Hindi from a simple topic.

Each story is returned as:
  {
    "title": str,
    "language": "bn" | "hi",
    "scenes": [
        {
            "narration": str,          # the voice-over text for this scene
            "visual_prompt": str,       # English prompt for the image/video model
            "emotion": str,            # happy / sad / neutral / excited / dramatic
        },
        ...
    ]
  }
"""

import json
import requests
from config import OLLAMA_HOST, STORY_MODEL_BN, STORY_MODEL_HI


# ── System prompts ────────────────────────────────────────────────────

SYSTEM_PROMPT_BN = """তুমি একজন পেশাদার ভিডিও স্ক্রিপ্ট লেখক।
ব্যবহারকারী একটি টপিক দেবে। তোমাকে সেই টপিকে একটি তথ্যবহুল, আকর্ষণীয় ভিডিও স্ক্রিপ্ট লিখতে হবে।

নিয়ম:
1. স্ক্রিপ্টটি {num_scenes}টি দৃশ্যে (scene) ভাগ করো।
2. প্রতিটি দৃশ্যের জন্য দাও:
   - narration: বাংলায় ভয়েস-ওভার টেক্সট (প্রতিটি ২-৪ বাক্য)
   - visual_prompt: ইংরেজিতে একটি বিস্তারিত প্রম্পট যা AI দিয়ে সিনেমাটিক ভিডিও/ছবি বানাবে
   - emotion: এই দৃশ্যের আবেগ (happy / sad / neutral / excited / dramatic / calm)

৩. স্ক্রিপ্ট তথ্যবহুল হতে হবে, শুধু গল্প নয়।
4. ভাষা সাবলীল ও প্রাকৃতিক হতে হবে।

শুধু এই JSON ফরম্যাটে উত্তর দাও, অন্য কিছু নয়:
{{
  "title": "ভিডিওর শিরোনাম",
  "scenes": [
    {{
      "narration": "বাংলা ন্যারেশন টেক্সট",
      "visual_prompt": "English visual description for AI video generation, cinematic, detailed",
      "emotion": "happy"
    }}
  ]
}}"""

SYSTEM_PROMPT_HI = """तुम एक पेशेवर वीडियो स्क्रिप्ट लेखक हो।
उपयोगकर्ता एक टॉपिक देगा। तुम्हें उस टॉपिक पर एक जानकारीपूर्ण, आकर्षक वीडियो स्क्रिप्ट लिखनी है।

नियम:
1. स्क्रिप्ट को {num_scenes} दृश्यों (scenes) में बांटो।
2. हर दृश्य के लिए दो:
   - narration: हिंदी में वॉयस-ओवर टेक्स्ट (हर एक २-४ वाक्य)
   - visual_prompt: अंग्रेजी में एक विस्तृत प्रॉम्प्ट जो AI से सिनेमैटिक वीडियो/तस्वीर बनाएगा
   - emotion: इस दृश्य का भाव (happy / sad / neutral / excited / dramatic / calm)

3. स्क्रिप्ट जानकारीपूर्ण होनी चाहिए, सिर्फ कहानी नहीं।
4. भाषा सहज और प्राकृतिक होनी चाहिए।

केवल इस JSON प्रारूप में उत्तर दो, और कुछ नहीं:
{{
  "title": "वीडियो का शीर्षक",
  "scenes": [
    {{
      "narration": "हिंदी नैरेशन टेक्स्ट",
      "visual_prompt": "English visual description for AI video generation, cinematic, detailed",
      "emotion": "happy"
    }}
  ]
}}"""


def _num_scenes_for_length(length: str) -> int:
    """Return number of scenes based on video length preference."""
    if length == "short":
        return 3
    elif length == "long":
        return 6
    else:
        return 4


def _call_ollama(model: str, system_prompt: str, user_message: str) -> str:
    """Call the Ollama API and return the raw text response."""
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.8,
            "top_p": 0.9,
        },
    }
    resp = requests.post(url, json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]


def generate_story(topic: str, language: str, length: str = "short") -> dict:
    """
    Generate a video script from a topic.

    Args:
        topic:   The video topic, e.g. "সৌরজগতের রহস্য" or "महानगर पलायन"
        language: "bn" or "hi"
        length:   "short" (~60 s) or "long" (~3-5 min)

    Returns:
        dict with keys: title, language, scenes[]
    """
    num_scenes = _num_scenes_for_length(length)

    if language == "hi":
        system_prompt = SYSTEM_PROMPT_HI.format(num_scenes=num_scenes)
        model = STORY_MODEL_HI
    else:
        system_prompt = SYSTEM_PROMPT_BN.format(num_scenes=num_scenes)
        model = STORY_MODEL_BN

    user_message = f"টপিক: {topic}" if language == "bn" else f"टॉपिक: {topic}"

    raw = _call_ollama(model, system_prompt, user_message)

    # Parse JSON — Ollama sometimes wraps in markdown code blocks
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    story = json.loads(raw)

    # Enrich
    story["language"] = language
    story["topic"] = topic
    story["length"] = length

    return story


def regenerate_scene(story: dict, scene_index: int, instruction: str) -> dict:
    """
    Regenerate a single scene based on user's edit instruction.
    Returns the updated scene dict.
    """
    scene = story["scenes"][scene_index]
    lang = story.get("language", "bn")

    if lang == "hi":
        sys_prompt = """तुम एक वीडियो स्क्रिप्ट संपादक हो। दृश्य को निर्देशानुसार बदलो।
केवल JSON में उत्तर दो:
{"narration": "...", "visual_prompt": "...", "emotion": "..."}"""
        user_msg = f"मूल दृश्य:\n{json.dumps(scene, ensure_ascii=False)}\n\nनिर्देश: {instruction}"
        model = STORY_MODEL_HI
    else:
        sys_prompt = """তুমি একজন ভিডিও স্ক্রিপ্ট এডিটর। দৃশ্যটি নির্দেশ অনুযায়ী পরিবর্তন করো।
শুধু JSON এ উত্তর দাও:
{"narration": "...", "visual_prompt": "...", "emotion": "..."}"""
        user_msg = f"মূল দৃশ্য:\n{json.dumps(scene, ensure_ascii=False)}\n\nনির্দেশ: {instruction}"
        model = STORY_MODEL_BN

    raw = _call_ollama(model, sys_prompt, user_msg)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    updated = json.loads(raw)

    # Merge — keep any keys the model didn't return
    for key in ("narration", "visual_prompt", "emotion"):
        if key in updated:
            scene[key] = updated[key]

    return scene
