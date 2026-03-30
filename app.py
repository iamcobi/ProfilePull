import os
import sys
import uuid
import time
import threading
from flask import Flask, request, jsonify, render_template, Response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import db
from src.core.config import config_manager
from src.core.detector import detect_url_type
from src.core.profile_manager import download_profile, download_single_video

app = Flask(__name__)

# Global dict to track download task progress for SSE
# Format: { task_id: {"msg": "...", "pct": 0, "status": "running"} }
running_tasks = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config", methods=["GET", "POST"])
def config_api():
    if request.method == "POST":
        data = request.json
        if "base_dir" in data:
            config_manager.base_dir = data["base_dir"]
        return jsonify({"status": "success", "base_dir": config_manager.base_dir})
    return jsonify({"base_dir": config_manager.base_dir})

@app.route("/api/history", methods=["GET"])
def get_history():
    downloads = db.get_all_downloads()
    # attach video counts
    for d in downloads:
        vids = db.get_all_videos_for_download(d["id"])
        d["video_count"] = len(vids)
    return jsonify({"downloads": downloads})

@app.route("/api/history", methods=["DELETE"])
def delete_history():
    db.clear_history()
    return jsonify({"status": "cleared"}), 200

@app.route("/api/history/<int:download_id>", methods=["DELETE"])
def delete_single_history(download_id):
    db.delete_download(download_id)
    return jsonify({"status": "deleted"}), 200

@app.route("/api/check_duplicate", methods=["POST"])
def check_duplicate():
    data = request.json
    url = data.get("url", "").strip()
    try:
        parsed = detect_url_type(url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if parsed["content_type"] == "profile":
        downloads = db.get_all_downloads()
        existing = [d for d in downloads if d["username"].lower() == parsed["username"].lower()]
        if existing:
            platforms = list(set([d["platform"] for d in existing]))
            return jsonify({
                "is_duplicate": True, 
                "parsed": parsed,
                "existing_platforms": platforms
            })
    
    return jsonify({"is_duplicate": False, "parsed": parsed})

@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.json
    url = data.get("url", "").strip()
    
    if not config_manager.base_dir:
        return jsonify({"error": "Please set a download location in Settings first."}), 400

    try:
        parsed = detect_url_type(url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    task_id = str(uuid.uuid4())
    label = f"@{parsed['username']}" if parsed["content_type"] == "profile" else "Single Video"
    
    running_tasks[task_id] = {
        "msg": "Starting download...",
        "pct": 0,
        "status": "running",
        "label": label
    }

    def progress_callback(msg, pct, total=None):
        if task_id in running_tasks:
            running_tasks[task_id]["msg"] = msg
            running_tasks[task_id]["pct"] = pct
            if total is not None:
                running_tasks[task_id]["total"] = total

    def task_thread():
        try:
            if parsed["content_type"] == "profile":
                download_profile(url, parsed["username"], parsed["platform"], config_manager.base_dir, progress_callback)
            else:
                download_single_video(url, config_manager.base_dir, progress_callback)
            
            if task_id in running_tasks:
                running_tasks[task_id]["status"] = "completed"
                running_tasks[task_id]["pct"] = 100
        except Exception as e:
            if task_id in running_tasks:
                running_tasks[task_id]["status"] = "error"
                running_tasks[task_id]["msg"] = str(e)

    threading.Thread(target=task_thread, daemon=True).start()
    return jsonify({"task_id": task_id, "label": label})

@app.route("/api/progress/<task_id>")
def progress_stream(task_id):
    def generate():
        while True:
            state = running_tasks.get(task_id)
            if not state:
                yield f"data: {{\"status\": \"error\", \"msg\": \"Task not found\"}}\n\n"
                break
                
            import json
            yield f"data: {json.dumps(state)}\n\n"
            
            if state["status"] in ["completed", "error"]:
                break
            time.sleep(0.5)
            
    return Response(generate(), mimetype="text/event-stream")

@app.route("/api/open_folder", methods=["POST"])
def open_folder():
    import subprocess
    data = request.json
    path = data.get("path")
    if path and os.path.exists(path):
        subprocess.Popen(f'explorer "{os.path.normpath(path)}"')
        return jsonify({"status": "success"})
    return jsonify({"error": "Path not found"}), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
