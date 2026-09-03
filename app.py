"""
Main Flask application — AI Video Creator.

Workflow:
  1. User enters a topic + language + length
  2. AI generates a story/script (user can review & edit)
  3. User approves → voice-over generated
  4. AI video clips generated
  5. Subtitles generated from voice
  6. Everything assembled into final MP4

Run:  python app.py
Open: http://localhost:5000
"""

import os
import json
import uuid
import threading
import traceback
from flask import Flask, request, jsonify, send_from_directory
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, OUTPUT_DIR, TEMP_DIR

app = Flask(__name__, static_folder="static")

# ── In-memory project store (use SQLite for persistence) ────────────
projects = {}

# ── Background task tracking ────────────────────────────────────────
tasks = {}


def _task_id():
    return uuid.uuid4().hex[:12]


# ════════════════════════════════════════════════════════════════════
#  API ROUTES
# ════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve the main UI."""
    return send_from_directory("static", "index.html")


@app.route("/api/voices", methods=["GET"])
def list_voices():
    """List available TTS voices."""
    from voice_over import VoiceOverGenerator
    gen = VoiceOverGenerator()
    return jsonify(gen.list_voices())


@app.route("/api/styles", methods=["GET"])
def list_styles():
    """List available video styles."""
    from video_generator import VideoGenerator
    return jsonify(VideoGenerator.STYLE_PRESETS)


@app.route("/api/story/generate", methods=["POST"])
def api_generate_story():
    """
    Generate a story script from a topic.

    Body: {topic, language ("bn"|"hi"), length ("short"|"long")}
    """
    from story_generator import generate_story

    data = request.json
    topic = data.get("topic", "").strip()
    language = data.get("language", "bn")
    length = data.get("length", "short")

    if not topic:
        return jsonify({"error": "Topic required"}), 400

    try:
        story = generate_story(topic, language, length)
        project_id = uuid.uuid4().hex[:12]
        projects[project_id] = {
            "id": project_id,
            "story": story,
            "status": "story_generated",
            "voice_key": data.get("voice_key"),
            "style": data.get("style", "cinematic"),
        }
        return jsonify({
            "project_id": project_id,
            "story": story,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/story/edit_scene", methods=["POST"])
def api_edit_scene():
    """
    Edit/regenerate a single scene.

    Body: {project_id, scene_index, instruction}
    """
    from story_generator import regenerate_scene

    data = request.json
    project = projects.get(data["project_id"])
    if not project:
        return jsonify({"error": "Project not found"}), 404

    try:
        updated = regenerate_scene(
            project["story"],
            data["scene_index"],
            data["instruction"],
        )
        return jsonify({"scene": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/story/update_scene", methods=["POST"])
def api_update_scene():
    """
    Manually update scene text (user's direct edits).

    Body: {project_id, scene_index, narration?, visual_prompt?, emotion?}
    """
    data = request.json
    project = projects.get(data["project_id"])
    if not project:
        return jsonify({"error": "Project not found"}), 404

    scene = project["story"]["scenes"][data["scene_index"]]
    for field in ("narration", "visual_prompt", "emotion"):
        if field in data:
            scene[field] = data[field]

    return jsonify({"scene": scene})


@app.route("/api/story/approve", methods=["POST"])
def api_approve_story():
    """
    Approve the story and start the full video generation pipeline.
    This kicks off a background task.

    Body: {project_id, voice_key?, style?, burn_subs?}
    """
    data = request.json
    project_id = data["project_id"]
    project = projects.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    voice_key = data.get("voice_key", project.get("voice_key"))
    style = data.get("style", project.get("style", "cinematic"))
    burn_subs = data.get("burn_subs", True)

    task_id = _task_id()
    tasks[task_id] = {
        "id": task_id,
        "project_id": project_id,
        "status": "queued",
        "step": "",
        "progress": 0,
        "error": None,
        "result_path": None,
    }

    thread = threading.Thread(
        target=_run_pipeline,
        args=(project_id, task_id, voice_key, style, burn_subs),
        daemon=True,
    )
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/api/task/<task_id>", methods=["GET"])
def api_task_status(task_id):
    """Poll task progress."""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route("/api/project/<project_id>", methods=["GET"])
def api_get_project(project_id):
    """Get project details."""
    project = projects.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project)


@app.route("/download/<path:filename>")
def download_file(filename):
    """Download a generated video."""
    return send_from_directory(str(OUTPUT_DIR), filename, as_attachment=True)


# ════════════════════════════════════════════════════════════════════
#  BACKGROUND PIPELINE
# ════════════════════════════════════════════════════════════════════

def _update_task(task_id, **kwargs):
    if task_id in tasks:
        tasks[task_id].update(kwargs)


def _run_pipeline(project_id, task_id, voice_key, style, burn_subs):
    """Run the full video generation pipeline in background."""
    try:
        project = projects[project_id]
        story = project["story"]
        language = story["language"]
        scenes = story["scenes"]

        # ── Step 1: Voice-over ──
        _update_task(task_id, status="running", step="ভয়েস-ওভার তৈরি হচ্ছে...", progress=10)
        from voice_over import VoiceOverGenerator
        tts = VoiceOverGenerator()
        voice_results = tts.generate_for_scenes(
            scenes, language, voice_key,
            output_dir=str(TEMP_DIR / project_id / "audio"),
        )

        # ── Step 2: Video clips ──
        _update_task(task_id, step="AI ভিডিও তৈরি হচ্ছে...", progress=30)
        from video_generator import VideoGenerator
        vg = VideoGenerator(style=style)
        video_results = vg.generate_for_scenes(
            scenes,
            voice_durations=voice_results,
            output_dir=str(TEMP_DIR / project_id / "video"),
            style=style,
        )

        # ── Step 3: Subtitles ──
        _update_task(task_id, step="সাবটাইটেল তৈরি হচ্ছে...", progress=70)
        from subtitle_generator import SubtitleGenerator
        sg = SubtitleGenerator()
        subtitle_results = sg.generate_for_scenes(
            voice_results, language,
            output_dir=str(TEMP_DIR / project_id / "subs"),
        )

        # ── Step 4: Assembly ──
        _update_task(task_id, step="ফাইনাল ভিডিও তৈরি হচ্ছে...", progress=85)
        from video_assembler import VideoAssembler
        va = VideoAssembler()
        final_path = va.assemble(
            video_results,
            voice_results,
            subtitle_results,
            title=story.get("title", "video"),
            burn_subs=burn_subs,
        )

        _update_task(
            task_id,
            status="done",
            step="সম্পূর্ণ!",
            progress=100,
            result_path=os.path.basename(final_path),
        )
        project["status"] = "completed"
        project["output_file"] = os.path.basename(final_path)

    except Exception as e:
        traceback.print_exc()
        _update_task(task_id, status="error", error=str(e))


# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n🎬 AI Video Creator")
    print(f"   Open: http://localhost:{FLASK_PORT}")
    print(f"   Debug: {FLASK_DEBUG}\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
