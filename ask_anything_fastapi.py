import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from ai_workflow_engine import extract_and_decide_with_gemini, dispatch_actions

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
    channels: Optional[List[str]] = (
        None  # No longer used for action detection, only as a potential hint/filter if re-introduced
    )
    callback_url: Optional[str] = None


@app.post("/ask")
async def ask(payload: RequestPayload):
    # Gemini now determines the action and extracts params
    ai_decision = await extract_and_decide_with_gemini(payload.message)
    action = ai_decision.get("action")
    params = ai_decision.get("params")
    print(f"AI Decision: action={action}, params={params}")

    if action == "no_action" or action == "error":
        return JSONResponse(
            {"error": params.get("message", "AI could not determine a valid action.")},
            status_code=400,
        )

    # Note: If you removed checkboxes, payload.channels will always be empty.
    # The filtering logic below would only activate if you re-add channels and send them.
    if payload.channels and action not in payload.channels:
        return JSONResponse(
            {
                "error": f"AI decided to use '{action}', but you specified channels {payload.channels}. Please adjust your message or selected channels."
            },
            status_code=400,
        )

    # Dispatch the action identified by Gemini
    results = await dispatch_actions(action, params)
    return {"results": results}


@app.get("/")
def get_ui(request: Request):
    return templates.TemplateResponse(
        "ask_anything_ai_interface.html", {"request": request}
    )


@app.post("/preview")
async def preview(payload: RequestPayload):
    # Gemini determines the *single best* action for preview
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

    # If you want to allow filtering by UI channels, re-enable this:
    # if payload.channels and action not in payload.channels:
    #      return JSONResponse(
    #         {"error": f"AI decided to use '{action}' for preview, but you specified channels {payload.channels}. Please adjust your message or selected channels."}, status_code=400
    #     )

    # Generate preview for the single action Gemini decided
    preview_data = await dispatch_actions(action, params, preview=True)
    return {action: preview_data}  # Return a dictionary with the action as key


@app.get("/health")
def health_check():
    return {"status": "running"}
