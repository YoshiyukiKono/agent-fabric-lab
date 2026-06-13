import json
import os
import urllib.request
from fastapi import FastAPI
from pydantic import BaseModel

ROLE = os.environ.get("ROLE", "agent")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
USE_OLLAMA = os.environ.get("USE_OLLAMA", "false").lower() == "true"

app = FastAPI()

class Task(BaseModel):
    task: str

@app.get("/")
def root():
    return {"role": ROLE, "status": "running", "mode": "ollama" if USE_OLLAMA else "mock", "model": OLLAMA_MODEL if USE_OLLAMA else None}

@app.post("/run")
def run(task: Task):
    if USE_OLLAMA:
        prompt = (
            f"You are a {ROLE} Agent in a multi-agent knowledge production pipeline. "
            "Answer concisely in Japanese. "
            f"Input: {task.task}"
        )
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as res:
            data = json.loads(res.read().decode("utf-8"))
        output = data.get("response", "")
    else:
        if ROLE == "researcher":
            output = f"Research notes for: {task.task}"
        elif ROLE == "architect":
            output = f"Structured plan based on: {task.task}"
        elif ROLE == "reviewer":
            output = f"Review comments for: {task.task}"
        else:
            output = f"{ROLE} processed: {task.task}"

    return {"role": ROLE, "input": task.task, "output": output}
