"""Adviser-only areas: document library, assistant (RAG), email."""
from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query

from app.api.deps import llm_dep, retriever_dep, settings_dep, storage_dep
from app.core.auth import Principal, require_advisor
from app.core.config import Settings
from app.core.db import get_conn
from app.core.http import Paging, no_content, ok
from app.core.rate_limit import llm_rate_limit
from app.email import drafting, service as email_service
from app.llm.base import LLMRouter
from app.rag.retrieval import Retriever
from app.schemas.models import AssistantQuery, DraftRequest, EmailLinkBody
from app.services import assistant, documents
from app.storage.base import Storage

router = APIRouter()


# ------------------------------------------------------------------------------------------------ documents
@router.get("/documents", tags=["documents"])
def list_documents(
    paging: Paging = Depends(), category: Optional[Literal["policy_wording", "internal_process", "company_policy", "regulation"]] = None,
    insurer_id: Optional[UUID] = None, search: Optional[str] = Query(None, max_length=100), sort: Optional[str] = Query(None),
    conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor),
):
    return ok(documents.list_documents(conn, paging, category, insurer_id, search, sort))


@router.get("/documents/{document_id}", tags=["documents"])
def get_document(document_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(documents.get_document(conn, document_id))


@router.get("/documents/{document_id}/url", tags=["documents"])
def document_url(document_id: UUID, conn: psycopg.Connection = Depends(get_conn), settings: Settings = Depends(settings_dep),
                 storage: Storage = Depends(storage_dep), p: Principal = Depends(require_advisor)):
    return ok(documents.document_url(conn, settings, storage, p, document_id))


# ----------------------------------------------------------------------------------------------- assistant
@router.post("/assistant/query", tags=["assistant"])
def assistant_query(body: AssistantQuery, conn: psycopg.Connection = Depends(get_conn), retriever: Retriever = Depends(retriever_dep),
                    llm: LLMRouter = Depends(llm_dep), p: Principal = Depends(llm_rate_limit)):
    return ok(assistant.query(conn, retriever, llm, p, body))


@router.get("/assistant/conversations", tags=["assistant"])
def list_conversations(paging: Paging = Depends(), conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(assistant.list_conversations(conn, p, paging))


@router.get("/assistant/conversations/{conversation_id}", tags=["assistant"])
def get_conversation(conversation_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(assistant.get_conversation(conn, p, conversation_id))


@router.delete("/assistant/conversations/{conversation_id}", tags=["assistant"])
def delete_conversation(conversation_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    assistant.delete_conversation(conn, p, conversation_id)
    return no_content()


# --------------------------------------------------------------------------------------------------- email
@router.get("/email/status", tags=["email"])
def email_status(p: Principal = Depends(require_advisor)):
    return ok(email_service.status(p))


@router.get("/email/threads", tags=["email"])
def list_threads(
    paging: Paging = Depends(), client_id: Optional[UUID] = None, claim_id: Optional[UUID] = None,
    flagged: Optional[bool] = None, linked: Optional[bool] = None, unread: Optional[bool] = None,
    search: Optional[str] = Query(None, max_length=100), sort: Optional[str] = Query(None),
    conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor),
):
    return ok(email_service.list_threads(conn, p, paging, client_id=client_id, claim_id=claim_id, flagged=flagged,
                                         linked=linked, unread=unread, search=search, sort=sort))


@router.get("/email/threads/{thread_id}", tags=["email"])
def get_thread(thread_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(email_service.get_thread(conn, p, thread_id))


@router.put("/email/threads/{thread_id}/link", tags=["email"])
def put_link(thread_id: UUID, body: EmailLinkBody, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    return ok(email_service.set_link(conn, p, thread_id, body))


@router.delete("/email/threads/{thread_id}/link", tags=["email"])
def delete_link(thread_id: UUID, conn: psycopg.Connection = Depends(get_conn), p: Principal = Depends(require_advisor)):
    email_service.clear_link(conn, p, thread_id)
    return no_content()


@router.post("/email/drafts/generate", tags=["email"])
def generate_draft(body: DraftRequest, conn: psycopg.Connection = Depends(get_conn), llm: LLMRouter = Depends(llm_dep),
                   p: Principal = Depends(llm_rate_limit)):
    return ok(drafting.generate(conn, llm, p, body))


@router.get("/email/oauth/start", tags=["email"])
def oauth_start(p: Principal = Depends(require_advisor)):
    raise email_service.oauth_not_built()


@router.get("/email/oauth/callback", tags=["email"])
def oauth_callback(p: Principal = Depends(require_advisor)):
    raise email_service.oauth_not_built()
