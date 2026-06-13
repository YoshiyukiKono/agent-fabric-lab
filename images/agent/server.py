import json
import os
import urllib.request
from fastapi import FastAPI
from pydantic import BaseModel

ROLE = os.environ.get("ROLE", "agent")
MODEL = os.environ.get("MODEL", "llama3.2:1b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/generate")

TOOL_MAP = {
    "researcher": {"tool": "research", "description": "Research a topic and produce concise notes."},
    "architect": {"tool": "design", "description": "Transform research notes into a structured plan."},
    "reviewer": {"tool": "review", "description": "Review a plan and point out risks and improvements."},
}

app = FastAPI()

class ToolCall(BaseModel):
    input: dict

def current_tool():
    return TOOL_MAP.get(ROLE, {"tool": ROLE})["tool"]

@app.get("/")
def root():
    return {"name": ROLE, "status": "running", "protocol": "mini-mcp"}

@app.get("/.well-known/agent.json")
def manifest():
    info = TOOL_MAP.get(ROLE, {"tool": ROLE, "description": f"{ROLE} tool"})
    return {
        "name": ROLE,
        "protocol": "mini-mcp",
        "tools": [{
            "name": info["tool"],
            "description": info["description"],
            "endpoint": "/tools/run",
            "input_schema": {"task": "string"}
        }]
    }

def call_ollama(prompt):
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as res:
        data = json.loads(res.read().decode("utf-8"))
    return data.get("response", "")

@app.post("/tools/run")
def run(call: ToolCall):
    task = call.input.get("task", "")

    if ROLE == "researcher":
        prompt = "You are a Research Tool. Write concise research notes in Japanese. Topic: " + task
    elif ROLE == "architect":
        prompt = "You are a Design Tool. Convert the following notes into a structured plan in Japanese: " + task
    elif ROLE == "reviewer":
        prompt = "You are a Review Tool. Critically review the following plan in Japanese. Point out risks and improvements: " + task
    else:
        prompt = "Process this task in Japanese: " + task

    output = call_ollama(prompt)

    return {
        "agent": ROLE,
        "tool": current_tool(),
        "input": task,
        "output": output
    }
