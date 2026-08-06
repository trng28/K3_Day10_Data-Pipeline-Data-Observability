from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist"
ENV_PATH = ROOT / ".env"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

EDITABLE_CONFIG = {
    "LLM_PROVIDER": {"type": "choice", "choices": ["gemini", "openai", "anthropic", "openrouter", "ollama", "custom"]},
    "LLM_MODEL": {"type": "text"},
    "EMBEDDING_PROVIDER": {"type": "choice", "choices": ["openai", "local"]},
    "EMBEDDING_MODEL": {"type": "text"},
    "SOURCE_QUERY": {"type": "text"},
    "MAX_RESULTS": {"type": "int", "min": 10, "max": 500},
    "TOP_K": {"type": "int", "min": 1, "max": 20},
    "FRESHNESS_THRESHOLD_DAYS": {"type": "int", "min": 1, "max": 3650},
    "REFRESH_SOURCE": {"type": "bool"},
    "REFRESH_TEST_SET": {"type": "bool"},
    "RUN_RAGAS": {"type": "bool"},
    "CORRUPTION_DROP_RATE": {"type": "float", "min": 0, "max": 0.5},
    "CORRUPTION_BLANK_RATE": {"type": "float", "min": 0, "max": 0.5},
    "CORRUPTION_NOISE_RATE": {"type": "float", "min": 0, "max": 0.5},
    "CORRUPTION_STALE_RATE": {"type": "float", "min": 0, "max": 0.5},
    "CORRUPTION_DUPLICATE_RATE": {"type": "float", "min": 0, "max": 0.5},
}

DEFAULTS = {
    "LLM_PROVIDER": "gemini", "LLM_MODEL": "gemini-2.5-flash",
    "EMBEDDING_PROVIDER": "openai", "EMBEDDING_MODEL": "text-embedding-3-small",
    "SOURCE_QUERY": "agentic retrieval augmented generation large language model",
    "MAX_RESULTS": "100", "TOP_K": "4", "FRESHNESS_THRESHOLD_DAYS": "180",
    "REFRESH_SOURCE": "0", "REFRESH_TEST_SET": "0", "RUN_RAGAS": "0",
    "CORRUPTION_DROP_RATE": "0.10", "CORRUPTION_BLANK_RATE": "0.12",
    "CORRUPTION_NOISE_RATE": "0.12", "CORRUPTION_STALE_RATE": "0.10",
    "CORRUPTION_DUPLICATE_RATE": "0.08",
}

STEPS = {
    "crawl": [str(PYTHON), "script/run_crawl.py"],
    "baseline": [str(PYTHON), "script/run_phase1.py"],
    "comparison": [str(PYTHON), "script/run_corruption_flow.py"],
}
STEP_SEQUENCES = {
    **{name: [name] for name in STEPS},
    "all": ["crawl", "baseline", "comparison"],
}


def read_json(path: Path, fallback=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return fallback


def read_env() -> tuple[list[str], dict[str, str]]:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()
    return lines, values


def safe_config() -> dict[str, str | bool | int | float]:
    _, values = read_env()
    result = {}
    for key, schema in EDITABLE_CONFIG.items():
        raw = values.get(key, DEFAULTS[key])
        if schema["type"] == "bool":
            result[key] = raw.lower() in {"1", "true", "yes"}
        elif schema["type"] == "int":
            result[key] = int(raw)
        elif schema["type"] == "float":
            result[key] = float(raw)
        else:
            result[key] = raw
    return result


def write_config(updates: dict) -> None:
    lines, _ = read_env()
    normalized: dict[str, str] = {}
    for key, value in updates.items():
        if key not in EDITABLE_CONFIG:
            continue
        schema = EDITABLE_CONFIG[key]
        if schema["type"] == "bool":
            normalized[key] = "1" if bool(value) else "0"
        elif schema["type"] in {"int", "float"}:
            number = int(value) if schema["type"] == "int" else float(value)
            if number < schema["min"] or number > schema["max"]:
                raise ValueError(f"{key} must be between {schema['min']} and {schema['max']}")
            normalized[key] = str(number)
        elif schema["type"] == "choice":
            if value not in schema["choices"]:
                raise ValueError(f"Invalid value for {key}")
            normalized[key] = str(value)
        else:
            normalized[key] = str(value).replace("\r", " ").replace("\n", " ")

    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped and not stripped.startswith("#") else ""
        if key in normalized:
            output.append(f"{key}={normalized[key]}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in normalized.items():
        if key not in seen:
            output.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def quality(name: str):
    payload = read_json(ROOT / "data" / "quality" / f"{name}.json")
    if payload is None and name == "baseline":
        payload = read_json(ROOT / "data" / "quality" / "baseline_quality.json")
    return payload


def state_payload(name: str) -> dict:
    metrics = read_json(ROOT / "data" / "results" / f"{name}_metrics.json")
    answers = read_json(ROOT / "data" / "results" / f"{name}_answers.json", [])
    fresh_name = "freshness_report.json" if name == "baseline" else f"{name}_freshness.json"
    return {
        "name": name,
        "metrics": metrics,
        "quality": quality(name),
        "freshness": read_json(ROOT / "data" / "quality" / fresh_name),
        "answers": answers[:8] if isinstance(answers, list) else [],
    }


def dashboard() -> dict:
    raw = read_json(ROOT / "data" / "raw" / "crossref_records.json", [])
    clean = read_json(ROOT / "data" / "clean" / "papers_clean.json", [])
    return {
        "config": safe_config(),
        "summary": {"rawRecords": len(raw), "cleanRecords": len(clean)},
        "states": [state_payload(name) for name in ("baseline", "corrupted", "repaired")],
        "corruptionLog": read_json(ROOT / "data" / "results" / "corruption_log.json"),
        "steps": {
            "crawl": (ROOT / "data" / "raw" / "crossref_records.json").exists(),
            "baseline": (ROOT / "data" / "results" / "baseline_metrics.json").exists(),
            "comparison": (ROOT / "data" / "results" / "repaired_metrics.json").exists(),
        },
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[demo] {format % args}")

    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            return self.send_json(dashboard())
        if path == "/api/health":
            return self.send_json({"ok": True, "python": sys.version.split()[0]})
        self.serve_static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/config":
                write_config(self.read_body())
                return self.send_json({"ok": True, "config": safe_config()})
            if path.startswith("/api/run/"):
                step = path.rsplit("/", 1)[-1]
                if step not in STEP_SEQUENCES:
                    return self.send_json({"error": "Unknown pipeline step"}, 404)
                if not PYTHON.exists():
                    return self.send_json({"error": "Missing .venv Python. Run uv sync first."}, 400)
                process_env = {
                    **os.environ,
                    "HF_HUB_OFFLINE": "1",
                    "TRANSFORMERS_OFFLINE": "1",
                    "HF_HUB_DISABLE_TELEMETRY": "1",
                }
                logs: list[str] = []
                exit_code = 0
                completed_steps: list[str] = []
                for current_step in STEP_SEQUENCES[step]:
                    logs.append(f"\n{'=' * 16} {current_step.upper()} {'=' * 16}")
                    process = subprocess.run(
                        STEPS[current_step], cwd=ROOT, env=process_env, text=True,
                        capture_output=True, timeout=1800,
                    )
                    logs.extend(part.strip() for part in (process.stdout, process.stderr) if part.strip())
                    exit_code = process.returncode
                    if exit_code != 0:
                        logs.append(f"Pipeline stopped: {current_step} failed with exit code {exit_code}.")
                        break
                    completed_steps.append(current_step)
                output = "\n".join(logs).strip()
                return self.send_json({
                    "ok": exit_code == 0, "exitCode": exit_code,
                    "completedSteps": completed_steps,
                    "output": output[-60000:], "dashboard": dashboard(),
                }, 200 if exit_code == 0 else 500)
        except subprocess.TimeoutExpired as exc:
            return self.send_json({"error": "Step timed out after 30 minutes", "output": str(exc)}, 504)
        except Exception as exc:
            return self.send_json({"error": str(exc)}, 400)
        self.send_json({"error": "Not found"}, 404)

    def serve_static(self, request_path: str):
        relative = request_path.lstrip("/") or "index.html"
        target = (DIST / relative).resolve()
        if not str(target).startswith(str(DIST.resolve())) or not target.is_file():
            target = DIST / "index.html"
        if not target.exists():
            return self.send_json({"error": "Frontend is not built. Run npm run build in frontend/."}, 404)
        content = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    host, port = "127.0.0.1", 8787
    print(f"Pipeline demo running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
