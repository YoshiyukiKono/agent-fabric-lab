import json
import threading
import time
import uuid
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PIPELINE = [
    ("Researcher", "http://researcher/run"),
    ("Architect", "http://architect/run"),
    ("Reviewer", "http://reviewer/run"),
]

JOBS = {}

def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as res:
        return json.loads(res.read().decode("utf-8"))

def run_pipeline(job_id, task):
    JOBS[job_id]["status"] = "running"
    current = task
    outputs = []
    try:
        for name, url in PIPELINE:
            JOBS[job_id]["current_agent"] = name
            result = post_json(url, {"task": current})
            outputs.append((name, result))
            JOBS[job_id]["outputs"] = outputs
            current = result.get("output", current)
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["current_agent"] = "done"
    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)

def html_page(task="", job_id=None):
    job_html = ""
    if job_id:
        job_html = f'<p>Job accepted: <code>{job_id}</code></p><p><a href="/result?id={job_id}">View result</a></p>'
    return f"""
<!doctype html><html><head><meta charset="utf-8"><title>Agent Orchestrator</title>
<style>body{{font-family:sans-serif;margin:40px}}textarea{{width:720px;height:120px}}code{{background:#eee;padding:2px 4px}}</style>
</head><body><h1>Agent Orchestrator</h1><p>Pipeline: Researcher → Architect → Reviewer</p>
<form method="POST" action="/run"><textarea name="task">{task}</textarea><br><button type="submit">Submit Job</button></form>{job_html}
</body></html>""".encode("utf-8")

def result_page(job_id):
    job = JOBS.get(job_id)
    if not job:
        return f"<html><body><h1>Job not found</h1><p>{job_id}</p></body></html>".encode("utf-8")
    rows = ""
    for name, result in job.get("outputs", []):
        rows += f"<tr><td>{name}</td><td><pre>{result.get('input','')}</pre></td><td><pre>{result.get('output','')}</pre></td></tr>"
    refresh = '<meta http-equiv="refresh" content="3">' if job["status"] in ["queued", "running"] else ""
    error = f"<p style='color:red;'>Error: {job.get('error','')}</p>" if job["status"] == "failed" else ""
    return f"""
<!doctype html><html><head><meta charset="utf-8">{refresh}<title>Agent Job Result</title>
<style>body{{font-family:sans-serif;margin:40px}}table{{border-collapse:collapse;margin-top:24px}}th,td{{border:1px solid #ccc;padding:8px 12px;vertical-align:top}}th{{background:#f0f0f0}}pre{{white-space:pre-wrap}}code{{background:#eee;padding:2px 4px}}</style>
</head><body><h1>Agent Job Result</h1><p>Job ID: <code>{job_id}</code></p><p>Status: <b>{job['status']}</b></p><p>Current Agent: <b>{job.get('current_agent','-')}</b></p><p>Task: {job.get('task','')}</p>{error}
<table><tr><th>Agent</th><th>Input</th><th>Output</th></tr>{rows}</table><p><a href="/">Back</a></p></body></html>""".encode("utf-8")

class Handler(BaseHTTPRequestHandler):
    def send_html(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/result":
            params = urllib.parse.parse_qs(parsed.query)
            self.send_html(result_page(params.get("id", [""])[0]))
        else:
            self.send_html(html_page())
    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/run":
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get("Content-Length", 0))
        params = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        task = params.get("task", [""])[0]
        job_id = str(uuid.uuid4())[:8]
        JOBS[job_id] = {"status": "queued", "task": task, "created_at": time.time(), "current_agent": "-", "outputs": []}
        threading.Thread(target=run_pipeline, args=(job_id, task), daemon=True).start()
        self.send_html(html_page(task, job_id))

HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
