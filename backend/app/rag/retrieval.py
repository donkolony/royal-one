"""Retrieval behind a small interface (docs/ARCHITECT.md section 8.3).

FtsRetriever uses PostgreSQL full-text search: no external service, deterministic, offline. Vector search can be added as
another Retriever once an embedding model is chosen and verified.

Known limitation: stemming does not connect every paraphrase (a question saying "notify" may not match text saying
"notification"). The golden-question tests exist to catch this on the demo corpus.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import List, Optional, Protocol
from uuid import UUID

import psycopg

from app.core.db import fetch_all, fetch_one

_STOP = set("""
a about above after again all also am an and any are as at be because been before being below between both but by can could did do
does doing down during each few for from further had has have having he her here hers him his how i if in into is it its itself just
me more most my no nor not now of off on once only or other our out over own same she should so some such than that the their theirs
them then there these they this those through to too under until up us very was we were what when where which while who whom why will
with would you your yours please tell give explain describe list say does need needs must typical usual
""".split())


@dataclass
class Chunk:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    category: str
    is_synthetic: bool
    page: int
    content: str
    matched: int = 0
    score: float = 0.0
    rank: float = 0.0


@dataclass
class Filters:
    categories: List[str]
    insurer_id: Optional[UUID] = None
    document_ids: Optional[List[UUID]] = None


class Retriever(Protocol):
    def search(self, conn: psycopg.Connection, question: str, filters: Filters, k: int = 6) -> List[Chunk]: ...


def keywords(text: str, limit: int = 12) -> List[str]:
    seen: List[str] = []
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if len(tok) >= 3 and tok not in _STOP and tok not in seen:
            seen.append(tok)
    return seen[:limit]


class FtsRetriever:
    """Keyword OR-query, ranked by how many question terms match, weighted by how rare each term is (IDF).

    A rare term such as "notification" says more about which passage answers the question than a term such as
    "claim" that appears on every page. The relevance floor (`min_match`) is what makes off-topic questions return
    nothing, so the model is never asked to answer from irrelevant text.
    """

    def _idf(self, conn: psycopg.Connection, kws: List[str]) -> List[float]:
        exprs = ", ".join(f"count(*) filter (where ch.tsv @@ to_tsquery('english', %s)) as df{i}" for i in range(len(kws)))
        row = fetch_one(
            conn,
            f"select count(*) as n, {exprs} from document_chunks ch join documents d on d.id = ch.document_id where d.status = 'indexed'",
            kws,
        )
        n = row["n"]
        return [math.log(1 + n / (row[f"df{i}"] + 1)) for i in range(len(kws))]

    def search(self, conn: psycopg.Connection, question: str, filters: Filters, k: int = 6) -> List[Chunk]:
        kws = keywords(question)
        if not kws:
            return []
        idf = self._idf(conn, kws)
        # Keywords are [a-z0-9]+ only, so they cannot break to_tsquery syntax; they are still passed as parameters.
        any_query = " | ".join(kws)
        matched_expr = " + ".join(["(ch.tsv @@ to_tsquery('english', %s))::int"] * len(kws))
        score_expr = " + ".join(["(ch.tsv @@ to_tsquery('english', %s))::int * %s::float8"] * len(kws))
        where = ["d.status = 'indexed'", "ch.tsv @@ to_tsquery('english', %s)"]
        where_params: list = [any_query]
        if filters.categories:
            where.append("d.category = any(%s)")
            where_params.append(filters.categories)
        if filters.insurer_id:
            where.append("d.insurer_id = %s")
            where_params.append(filters.insurer_id)
        if filters.document_ids:
            where.append("d.id = any(%s)")
            where_params.append(filters.document_ids)
        min_match = max(1, math.ceil(len(kws) / 2))
        sql = f"""
            select * from (
              select ch.id as chunk_id, ch.document_id, d.title as document_title, d.category, d.is_synthetic,
                     ch.page, ch.content, ({matched_expr}) as matched, ({score_expr}) as score,
                     ts_rank_cd(ch.tsv, to_tsquery('english', %s)) as rank
              from document_chunks ch join documents d on d.id = ch.document_id
              where {' and '.join(where)}
            ) t
            where matched >= %s
            order by score desc, matched desc, rank desc, document_title, page, chunk_id
            limit %s
        """
        weighted = [x for kw, w in zip(kws, idf) for x in (kw, w)]
        params = kws + weighted + [any_query] + where_params + [min_match, k]
        rows = fetch_all(conn, sql, params)
        return [Chunk(**{**r, "rank": float(r["rank"]), "score": float(r["score"])}) for r in rows]


_SENT = re.compile(r"(?<=[.!?])\s+|\n+")  # sentence ends and line breaks (a heading is its own segment)


def best_quote(content: str, question: str, max_len: int = 300) -> str:
    """The stored sentence that best overlaps the question. Always copied from the source, never model-written."""
    kws = keywords(question)
    segments = [s.strip() for s in _SENT.split(content) if s.strip()] or [content.strip()]
    # A heading ("Section 3: Notifying a claim") has no closing punctuation: it is never the quote unless nothing else exists.
    sentences = [s for s in segments if s[-1] in ".!?"] or segments
    # Match on a 5-letter stem prefix so "notification" also finds "notify"; ties keep the earliest sentence.
    best = max(sentences, key=lambda s: sum(1 for w in kws if w[:5] in s.lower()))
    if len(best) <= max_len:
        return best
    cut = best[:max_len].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "…"
