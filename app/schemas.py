from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ToolCallRecord(BaseModel):
    tool: str
    arguments: dict
    success: bool
    error: str | None = None


class Source(BaseModel):
    kind: Literal["database", "document"]
    reference: str


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[ToolCallRecord] = []
    sources: list[Source] = []
