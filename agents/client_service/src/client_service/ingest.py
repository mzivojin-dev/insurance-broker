"""Embed policy PDFs into policy_chunks for search_policy_docs.

    uv run python -m client_service.ingest                  # every PDF in data/docs/out/policies
    uv run python -m client_service.ingest --client C-1042  # one client

Needs DATABASE_URL and VOYAGE_API_KEY. Run the seed first: it creates the policies rows and PDFs.
Re-running is safe: each policy's chunks are replaced, not appended.
"""

import argparse
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import psycopg
import voyageai
from pypdf import PdfReader

# 1024 dims, matches policy_chunks.embedding. search_policy_docs must embed queries with the same.
MODEL = "voyage-3.5"
BATCH = 128            # Voyage takes up to 1000 texts and 320k tokens per request
DEFAULT_ROOT = Path(__file__).resolve().parents[4] / "data" / "docs" / "out"

HEADING = re.compile(r"^(SECTION [IVX]+.*|[A-Z][A-Za-z /&-]{3,60})$")
POLICY_NO = re.compile(r"\bPOL-\d+(?:-\d+)?\b")


@dataclass
class Chunk:
    source_doc: str      # "policies/C-1042/HO3-2026.pdf#Exclusions"
    heading: str
    content: str


def chunk_policy(path: str, rel: str, max_chars: int = 2400) -> list[Chunk]:
    text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    chunks, heading, buf = [], "Declarations", []
    for line in text.splitlines():
        if HEADING.match(line.strip()) and buf:
            chunks += _flush(rel, heading, buf, max_chars)
            heading, buf = line.strip(), []
        elif HEADING.match(line.strip()):
            heading = line.strip()
        else:
            buf.append(line)
    return chunks + _flush(rel, heading, buf, max_chars)


def _flush(rel, heading, buf, max_chars):
    body = "\n".join(buf).strip()
    parts = [body[i:i + max_chars] for i in range(0, len(body), max_chars)] or [""]
    return [Chunk(f"{rel}#{heading}", heading, f"{heading}\n{p}") for p in parts if p]


def policy_id_for(chunks: list[Chunk], client_id: str, owned: dict[str, str]) -> str | None:
    """The first policy number in the document, if that policy belongs to the folder's client.

    A file filed under the wrong client is skipped rather than ingested, because policy_chunks
    rows are scoped through policies.client_id and would otherwise leak into another client's
    search.
    """
    for c in chunks:
        if m := POLICY_NO.search(c.content):
            return m.group() if owned.get(m.group()) == client_id else None
    return None


def embed(texts: list[str], vo: voyageai.Client) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        # a Voyage account without a payment method gets 3 requests a minute
        for wait in (0, 30, 60, 60):
            time.sleep(wait)
            try:
                out += vo.embed(texts[i:i + BATCH], model=MODEL, input_type="document").embeddings
                break
            except voyageai.error.RateLimitError:
                print(f"rate limited, retrying batch {i // BATCH + 1}")
        else:
            raise RuntimeError("still rate limited after 3 retries")
    return out


def ingest(conn: psycopg.Connection, policy_id: str, chunks: list[Chunk], vecs: list) -> int:
    with conn.transaction():
        conn.execute("DELETE FROM policy_chunks WHERE policy_id = %s", (policy_id,))
        conn.cursor().executemany(
            "INSERT INTO policy_chunks (policy_id, source_doc, content, embedding)"
            " VALUES (%s, %s, %s, %s::vector)",
            [(policy_id, c.source_doc, c.content, str(v))
             for c, v in zip(chunks, vecs, strict=True)],
        )
    return len(chunks)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                   help="folder holding policies/<client>/")
    p.add_argument("--client", help="only this client ID")
    args = p.parse_args()

    vo = voyageai.Client()   # reads VOYAGE_API_KEY
    pdfs = sorted((args.root / "policies").glob(f"{args.client or '*'}/*.pdf"))
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        owned = dict(conn.execute("SELECT policy_id, client_id FROM policies").fetchall())
        by_policy: dict[str, list[Chunk]] = defaultdict(list)
        clients = set(owned.values())
        skipped = []
        for pdf in pdfs:
            rel = pdf.relative_to(args.root).as_posix()
            if pdf.parent.name not in clients:   # e.g. --large PDFs left after a --small reseed
                skipped.append((rel, "client not in database"))
                continue
            if pdf.stem.endswith("_ugly"):    # rasterised copy, no text layer; OCR is not this step
                skipped.append((rel, "scanned copy"))
                continue
            chunks = chunk_policy(str(pdf), rel)
            if not chunks:
                skipped.append((rel, "no text"))
            elif pid := policy_id_for(chunks, pdf.parent.name, owned):
                by_policy[pid] += chunks
            else:
                skipped.append((rel, "no policy number belonging to this client"))

        # embed everything in shared batches (few requests), then replace each policy's rows
        vecs = iter(embed([c.content for cs in by_policy.values() for c in cs], vo))
        total = sum(ingest(conn, pid, cs, [next(vecs) for _ in cs])
                    for pid, cs in by_policy.items())

    for why in sorted({why for _, why in skipped}):
        rels = [rel for rel, w in skipped if w == why]
        print(f"skipped {len(rels)} ({why}), e.g. {rels[0]}")
    print(f"ingested {total} chunks for {len(by_policy)} policies from {len(pdfs)} files"
          f" ({len(skipped)} skipped)")


if __name__ == "__main__":
    main()
