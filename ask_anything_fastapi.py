import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from ai_workflow_engine import extract_and_decide_with_gemini, dispatch_actions

from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Ask-Anything AI Workflow Automation")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestPayload(BaseModel):
    message: str
    channels: Optional[List[str]] = None
    callback_url: Optional[str] = None


@app.post("/ask")
async def ask(payload: RequestPayload):
    ai_decision = await extract_and_decide_with_gemini(payload.message)
    action = ai_decision.get("action")
    params = ai_decision.get("params")
    print(f"AI Decision: action={action}, params={params}")

    if action in ("no_action", "error"):
        return JSONResponse(
            {"error": params.get("message", "AI could not determine a valid action.")},
            status_code=400,
        )

    if payload.channels and action not in payload.channels:
        return JSONResponse(
            {
                "error": f"AI decided to use '{action}', but you specified channels {payload.channels}. Please adjust your message or selected channels."
            },
            status_code=400,
        )

    results = await dispatch_actions(action, params)
    return {"results": results}


@app.get("/")
def get_ui(request: Request):
    return templates.TemplateResponse(
        "ask_anything_ai_interface.html", {"request": request}
    )


@app.post("/preview")
async def preview(payload: RequestPayload):
    ai_decision = await extract_and_decide_with_gemini(payload.message)
    action = ai_decision.get("action")
    params = ai_decision.get("params")
    print(f"AI Decision: action={action}, params={params}")

    if action == "no_action":
        return JSONResponse(
            {
                "error": params.get(
                    "message", "AI could not determine a valid action for preview."
                )
            },
            status_code=400,
        )
    elif action == "error":
        return JSONResponse(
            {
                "error": f"AI processing error: {params.get('message', 'Unknown error.')}"
            },
            status_code=500,
        )

    preview_data = await dispatch_actions(action, params, preview=True)
    return {action: preview_data}


@app.get("/health")
def health_check():
    return {"status": "running"}
