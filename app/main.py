"""A small Flask API that we ship through the secure CI/CD pipeline to Amazon ECS."""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

APP_VERSION = os.environ.get("APP_VERSION", "dev")

# ---- Logging: one JSON line per event, printed to stdout. ----
# On ECS, stdout goes straight to Amazon CloudWatch Logs, and JSON lines are
# easy to search with CloudWatch Logs Insights.
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_handler)


def log(level: str, message: str, **fields) -> None:
    record = {"time": datetime.now(timezone.utc).isoformat(), "level": level, "message": message}
    record.update(fields)
    logger.log(getattr(logging, level), json.dumps(record))


app = Flask(__name__)

# In-memory store, just for the demo. It resets when the container restarts.
TASKS: list[dict] = []


@app.before_request
def start_timer():
    g.start = time.perf_counter()


@app.after_request
def log_request(response):
    if request.path != "/health":  # health checks run every few seconds; skip the noise
        duration_ms = round((time.perf_counter() - g.start) * 1000, 1)
        log(
            "INFO",
            "request",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=duration_ms,
            version=APP_VERSION,
        )
    return response


@app.errorhandler(Exception)
def handle_error(exc):
    if isinstance(exc, HTTPException):  # 404, 405 etc. are normal, not crashes
        return jsonify(error=exc.description), exc.code
    log("ERROR", "unhandled_exception", error=type(exc).__name__, path=request.path)
    return jsonify(error="internal server error"), 500


@app.get("/")
def home():
    return jsonify(message="Hello from the AI-assisted secure CI/CD pipeline!", version=APP_VERSION)


@app.get("/health")
def health():
    return jsonify(status="ok", version=APP_VERSION)


@app.get("/api/tasks")
def list_tasks():
    return jsonify(tasks=TASKS)


@app.post("/api/tasks")
def add_task():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()

    # Validate input instead of trusting it
    if not title:
        return jsonify(error="'title' is required"), 400
    if len(title) > 200:
        return jsonify(error="'title' must be 200 characters or fewer"), 400

    task = {"id": len(TASKS) + 1, "title": title, "done": False}
    TASKS.append(task)
    log("INFO", "task_created", task_id=task["id"])
    return jsonify(task), 201


if __name__ == "__main__":
    # Local development only. In the container, gunicorn runs the app.
    app.run(host="127.0.0.1", port=8080, debug=False)
