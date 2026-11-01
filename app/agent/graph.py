"""Agent orchestration (Phase 2).

Planned LangGraph loop:
    1. LLM receives the user message plus TOOLS[*].json_schema().
    2. If it requests tool calls, validate arguments with the tool's input_model,
       execute, and append results (or errors) to the conversation.
    3. Repeat until the LLM produces a final answer.
    4. Return a ChatResponse with every tool call recorded and sources cited.
"""

from sqlalchemy.orm import Session

from app.schemas import ChatResponse


def run_agent(session: Session, message: str) -> ChatResponse:
    raise NotImplementedError("Agent orchestration is implemented in Phase 2.")
