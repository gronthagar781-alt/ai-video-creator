# 🎬 AI Video Creator — সম্পূর্ণ ফ্রি ও ওপেন-সোর্স

একটি ওয়েব অ্যাপ যা শুধু একটি **টপিক** থেকে সম্পূর্ণ ভিডিও তৈরি করে — বাংলা ও হিন্দিতে।

স্টোরি → ভয়েস-ওভার → সাবটাইটেল → সিনেমাটিক ভিডিও → ফাইনাল MP4 — সব অটোমেটিক, সব ফ্রি।

---

## ✨ ফিচার

| ফিচার | টুল | লাইসেন্স |
|-------|------|----------|
| স্টোরি জেনারেশন | Ollama + Qwen2.5 | MIT (ফ্রি) |
| ভয়েস-ওভার (TTS) | AI4Bharat IndicF5 | Apache-2.0 (ফ্রি) |
| সাবটাইটেল | OpenAI Whisper | MIT (ফ্রি) |
| AI ভিডিও | AnimateDiff + Stable Diffusion | Apache-2.0 (ফ্রি) |
| ভিডিও অ্যাসেম্বলি | FFmpeg | LGPL (ফ্রি) |
| ওয়েব UI | Flask + HTML/CSS/JS | BSD (ফ্রি) |

### কী কী পারবেন

1. ✅ শুধু টপিক দিন — AI স্টোরি ও স্ক্রিপ্ট তৈরি করবে
2. ✅ স্টোরি রিভিউ ও এডিট করুন (প্রতিটি দৃশ্য আলাদা করে)
3. ✅ AI দিয়ে যেকোনো দৃশ্য পরিবর্তন করুন
4. ✅ বাংলা ও হিন্দিতে ভয়েস-ওভার — একাধিক কণ্ঠে
5. ✅ সাবটাইটেল অটো-জেনারেট
6. ✅ সিনেমাটিক / রিয়ালিস্টিক / অ্যানিমেশন স্টাইল
7. ✅ ফাইনাল MP4 ডাউনলোড — YouTube/Facebook-এর জন্য রেডি
8. ✅ শর্ট (~60s) ও ফুল লেন্থ (~3-5 min) ভিডিও

---

## 📋 সিস্টেম রিকোয়ারমেন্ট

### ন্যূনতম (CPU — ধীর গতি)
- RAM: 16 GB
- Storage: 20 GB ফাঁকা
- OS: Windows 10/11, macOS, বা Linux (Ubuntu 20.04+)
- Python 3.10 বা তার ওপরে

### প্রস্তাবিত (GPU — দ্রুত গতি)
- GPU: NVIDIA RTX 3060 (12GB VRAM) বা ভালো
- RAM: 32 GB
- Storage: 50 GB ফাঁকা (মডেল ডাউনলোডের জন্য)
- Python 3.10+

---

## 🚀 ইনস্টলেশন (ধাপে ধাপে)

### ধাপ 1: Python ইনস্টল করুন

**Windows:** [python.org](https://www.python.org/downloads/) থেকে Python 3.10+ ডাউনলোড করুন।
ইনস্টল করার সময় "Add Python to PATH" চেক করতে ভুলবেন না।

**Linux (Ubuntu):**
```bash
sudo apt update && sudo apt install python3.10 python3-pip python3-venv -y
```

**macOS:**
```bash
brew install python@3.10
```

### ধাপ 2: FFmpeg ইনস্টল করুন

**Windows:**
1. [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) থেকে FFmpeg ডাউনলোড করুন
2. ZIP আনজিপ করে `C:\ffmpeg` এ রাখুন
3. `C:\ffmpeg\bin` কে System PATH-এ যোগ করুন
4. যাচাই করুন: `ffmpeg -version`

**Linux:**
```bash
sudo apt install ffmpeg -y
```

**macOS:**
```bash
brew install ffmpeg
```

### ধাপ 3: Ollama ইনস্টল করুন (স্টোরি জেনারেশনের জন্য)

1. [ollama.com/download](https://ollama.com/download) এ যান
2. আপনার OS অনুযায়ী ডাউনলোড ও ইনস্টল করুন
3. একটি মডেল পুল করুন (বাংলা/হিন্দি সাপোর্ট করে এমন):

```bash
# প্রস্তাবিত (ভালো মানের, 7B parameters)
ollama pull qwen2.5:7b

# হালকা বিকল্প (দ্রুত, কিন্তু কম মানের)
ollama pull qwen2.5:3b
```

4. যাচাই করুন:
```bash
ollama run qwen2.5:7b "বাংলায় একটি ছোট গল্প লিখো"
```

### ধাপ 4: প্রজেক্ট সেটআপ করুন

```bash
# ১. রিপো ক্লোন করুন
git clone https://github.com/gronthagar781-alt/ai-video-creator.git
cd ai-video-creator

# ২. Virtual environment তৈরি করুন
python -m venv venv

# ৩. Activate করুন
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# ৪. Python ডিপেন্ডেন্সি ইনস্টল করুন
pip install -r requirements.txt
```

### ধাপ 5: Noto Fonts ইনস্টল করুন (সাবটাইটেলের জন্য)

বাংলা ও হিন্দি সাবটাইটেল সঠিকভাবে দেখাতে Noto Sans ফন্ট লাগবে।

**Linux:**
```bash
sudo apt install fonts-noto-core fonts-noto-cjk -y
```

**Windows:** [Google Noto Fonts](https://fonts.google.com/noto) থেকে Noto Sans Bengali এবং Noto Sans Devanagari ডাউনলোড করে ইনস্টল করুন।

**macOS:** Homebrew দিয়ে:
```bash
brew install --cask font-noto-sans-bengali font-noto-sans-devanagari
```

### ধাপ 6: অ্যাপ চালু করুন

```bash
# Ollama চালু আছে কিনা যাচাই করুন
ollama serve

# নতুন terminal এ অ্যাপ চালু করুন
python app.py
```

ব্রাউজারে খুলুন: **http://localhost:5000**

---

## 🎯 ব্যবহার পদ্ধতি

1. **টপিক দিন** — যেমন "সুন্দরবনের বাঘ" বা "ताजमहल का इतिहास"
2. **ভাষা ও দৈর্ঘ্য নির্বাচন করুন** — বাংলা/হিন্দি, শর্ট/লং
3. **ভয়েস ও স্টাইল বাছুন** — নারী/পুরুষ কণ্ঠ, সিনেমাটিক/অ্যানিমেশন
4. **স্টোরি রিভিউ করুন** — প্রতিটি দৃশ্য এডিট করতে পারবেন
5. **এপ্রুভ করুন** — ভিডিও তৈরি শুরু হবে
6. **ডাউনলোড করুন** — ফাইনাল MP4 পেয়ে যাবেন

---

## 🔧 কাস্টম ভয়েস যোগ করা

নিজের ভয়েস যোগ করতে পারবেন:

1. `data/voice_prompts/` ফোল্ডারে একটি 5-12 সেকেন্ডের WAV ফাইল রাখুন
   - নাম দিন: `myvoice_female.wav` (বা `myvoice_male.wav`)
2. সেই ফাইলের ট্রান্সক্রিপ্ট একটি `.txt` ফাইলে রাখুন
   - নাম দিন: `myvoice_female.txt`
   - ভেতরে লিখুন ফাইলে যা বলা হয়েছে সেটা
3. অ্যাপ রিস্টার্ট করুন — নতুন ভয়েস ড্রপডাউনে দেখাবে

---

## ⚙️ কনফিগারেশন

`config.py` ফাইলে সব সেটিংস আছে। প্রয়োজনে পরিবর্তন করুন:

```python
# মডেল পরিবর্তন
STORY_MODEL_BN = "qwen2.5:7b"      # বাংলা স্টোরির জন্য
STORY_MODEL_HI = "qwen2.5:7b"      # হিন্দি স্টোরির জন্য

# ভিডিও কোয়ালিটি
VIDEO_WIDTH = 512                    # 768 বা 1024 করতে পারেন (ভালো GPU লাগবে)
VIDEO_HEIGHT = 512
VIDEO_FPS = 8                        # 12 বা 15 করতে পারেন
VIDEO_NUM_INFERENCE_STEPS = 25       # 50 করলে মান ভালো, সময় বেশি

# Whisper মডেল
WHISPER_MODEL = "base"               # tiny | base | small | medium | large
```

---

## 🐛 সমস্যা সমাধান

### Ollama সংযোগ ত্রুটি
```
Error: Connection refused
```
সমাধান: Ollama চালু আছে কিনা দেখুন:
```bash
ollama serve
# বা ওল্লামা অ্যাপ খুলুন
```

### TTS মডেল ডাউনলোড সময়
প্রথমবার IndicF5 মডেল ডাউনলোড হবে (~1.4 GB)। এটি একবারই হবে, এরপর লোকালি ক্যাশ হবে।

### GPU নেই (CPU তে চলছে)
- ভিডিও জেনারেশন ধীর হবে (প্রতিটি ক্লিপ 5-15 মিনিট)
- TTS গ্রহণযোগ্য গতিতে চলবে
- প্রস্তাবনা: Google Colab (ফ্রি GPU) তে চালান

### সাবটাইটেল ফন্ট সমস্যা
যদি বাংলা/হিন্দি অক্ষর সঠিক না দেখায়, নিশ্চিত করুন যে সিস্টেমে Noto Sans Bengali ও Noto Sans Devanagari ফন্ট ইনস্টল আছে।

### VRAM কম
`config.py` এ পরিবর্তন করুন:
```python
VIDEO_WIDTH = 384
VIDEO_HEIGHT = 384
VIDEO_FRAMES_SHORT = 8
```

---

## 📁 প্রজেক্ট স্ট্রাকচার

```
ai-video-creator/
├── app.py                    # Flask ওয়েব অ্যাপ
├── config.py                 # সব সেটিংস
├── story_generator.py        # AI স্টোরি জেনারেশন (Ollama)
├── voice_over.py             # TTS ভয়েস-ওভার (IndicF5)
├── video_generator.py        # AI ভিডিও জেনারেশন (AnimateDiff)
├── subtitle_generator.py     # সাবটাইটেল (Whisper)
├── video_assembler.py        # ভিডিও অ্যাসেম্বলি (FFmpeg)
├── requirements.txt          # Python ডিপেন্ডেন্সি
├── README.md                 # এই ফাইল
├── static/
│   └── index.html            # ওয়েব UI
├── data/
│   └── voice_prompts/        # কাস্টম ভয়েস ফাইল
├── outputs/                  # ফাইনাল ভিডিও
└── temp/                     # অস্থায়ী ফাইল
```

---

## 💰 খরচ

**সম্পূর্ণ ফ্রি।** কোনো API কী নেই, কোনো সাবস্ক্রিপশন নেই। সব কিছু আপনার কম্পিউটারে লোকালি চলে।

---

## 🔒 প্রাইভেসি

সব প্রসেসিং আপনার কম্পিউটারে হয়। কোনো ডেটা ইন্টারনেটে যায় না (মডেল ডাউনলোড ছাড়া)।

---

## 📌 টিপস

- **প্রথমবার ধীর হবে** — মডেল ডাউনলোড হবে। পরে দ্রুত হবে।
- **GPU থাকলে ভালো** — ভিডিও জেনারেশন 10-20 গুণ দ্রুত হবে।
- **শর্ট ভিডিও দিয়ে শুরু করুন** — টেস্ট করার জন্য শর্ট লেন্থ বাছুন।
- **ভিজ্যুয়াল প্রম্পট এডিট করুন** — ভিডিও মান উন্নত করতে ইংরেজি প্রম্পট বিস্তারিত করুন।
