from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.agent.graph import run_agent
from app.db.session import get_session
from app.schemas import ChatRequest, ChatResponse
from app.tools.registry import TOOLS

app = FastAPI(title="FoodOps AI", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/tools")
def list_tools() -> list[dict]:
    return [tool.json_schema() for tool in TOOLS.values()]


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, session: Session = Depends(get_session)) -> ChatResponse:
    try:
        return run_agent(session, request.message)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
