from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(
    title="NOX AI API",
    version="1.0"
)

# -------------------------
# Request Model
# -------------------------

class ChatRequest(BaseModel):
    prompt: str


# -------------------------
# Fake runtime memory
# (replace later with your real agents)
# -------------------------

analytics = {
    "messages": 0,
    "errors": 0,
    "start_time": datetime.now()
}

agents = [
    "planner",
    "coder",
    "memory",
    "analytics"
]


# -------------------------
# Chat Endpoint
# -------------------------

@app.post("/chat")
async def chat(request: ChatRequest):

    analytics["messages"] += 1

    prompt = request.prompt

    # Replace this with your forge pipeline
    response = f"NOX received: {prompt}"

    return {
        "status": "success",
        "message": response
    }


# -------------------------
# Analytics Endpoint
# -------------------------

@app.get("/analytics")
async def get_analytics():

    uptime = datetime.now() - analytics["start_time"]

    return {
        "messages": analytics["messages"],
        "errors": analytics["errors"],
        "uptime": str(uptime).split(".")[0]
    }


# -------------------------
# Agents Endpoint
# -------------------------

@app.get("/agents")
async def get_agents():

    return {
        "active_agents": agents,
        "count": len(agents)
    }


# -------------------------
# Health Check
# -------------------------

@app.get("/health")
async def health():

    return {
        "status": "running",
        "time": datetime.now()
    }