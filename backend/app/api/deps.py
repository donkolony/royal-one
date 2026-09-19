"""Shared FastAPI dependencies. Runtime services live on `app.state` so tests can swap them."""
from __future__ import annotations

from fastapi import Request

from app.core.config import Settings
from app.llm.base import LLMRouter
from app.rag.retrieval import Retriever
from app.storage.base import Storage


def settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def storage_dep(request: Request) -> Storage:
    return request.app.state.storage


def llm_dep(request: Request) -> LLMRouter:
    return request.app.state.llm


def retriever_dep(request: Request) -> Retriever:
    return request.app.state.retriever
