import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from ai_workflow_engine import detect_actions, dispatch_actions

app = FastAPI(title="Ask-Anything AI Workflow Automation")

templates = Jinja2Templates(directory="templates")

# Allow CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestPayload(BaseModel):
    message: str
    channels: Optional[List[str]] = None  # e.g. ["email", "slack", ...]
    callback_url: Optional[str] = None


@app.post("/ask")
async def ask(payload: RequestPayload):
    actions = detect_actions(payload.message, payload.channels)
    if not actions:
        return JSONResponse(
            {"error": "No valid actions detected from message"}, status_code=400
        )

    tasks = [dispatch_actions(action, payload.message) for action in actions]
    results = await asyncio.gather(*tasks)
    return {"results": results}


@app.get("/")
def get_ui(request: Request):
    return templates.TemplateResponse(
        "ask_anything_ai_interface.html", {"request": request}
    )


@app.post("/preview")
async def preview(payload: RequestPayload):
    previews = {}
    channels = payload.channels or []
    if not channels:
        channels = ["email", "slack", "telegram", "calendar"]

    for channel in channels:
        previews[channel] = await dispatch_actions(
            channel, payload.message, preview=True
        )

    return previews


@app.get("/health")
def health_check():
    return {"status": "running"}
