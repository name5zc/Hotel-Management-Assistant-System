from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


DEFAULT_KB_DIR = "knowledge"
_WORD_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fff]+")


@dataclass
class Chunk:
    source: str
    text: str


def _resolve_kb_dir() -> Path:
    kb_dir = os.environ.get("HOTEL_KB_DIR", DEFAULT_KB_DIR)
    return Path(kb_dir).expanduser().resolve()


def _tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    for m in _WORD_RE.finditer(text):
        tok = m.group(0).lower()
        if not tok:
            continue
        tokens.append(tok)
        # Add Chinese bi-grams for rough matching without external deps.
        if re.fullmatch(r"[\u4e00-\u9fff]+", tok) and len(tok) >= 2:
            tokens.extend(tok[i : i + 2] for i in range(len(tok) - 1))
    return tokens


def _build_chunks(kb_dir: Path) -> List[Chunk]:
    chunks: List[Chunk] = []
    if not kb_dir.exists():
        return chunks
    files = sorted(kb_dir.glob("*.md"))
    for f in files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        # Split by markdown headers; keep reasonable chunk size.
        sections = re.split(r"\n#{1,3}\s+", "\n" + content)
        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue
            for part in _split_long_text(sec, max_len=550):
                chunks.append(Chunk(source=f.name, text=part))
    return chunks


def _split_long_text(text: str, max_len: int) -> List[str]:
    if len(text) <= max_len:
        return [text]
    parts: List[str] = []
    current: List[str] = []
    cur_len = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line_len = len(line) + 1
        if cur_len + line_len > max_len and current:
            parts.append("\n".join(current))
            current = [line]
            cur_len = line_len
        else:
            current.append(line)
            cur_len += line_len
    if current:
        parts.append("\n".join(current))
    return parts


def search_policy(query: str, top_k: int = 3) -> Dict[str, object]:
    kb_dir = _resolve_kb_dir()
    chunks = _build_chunks(kb_dir)
    if not chunks:
        return {
            "answer": "知识库为空，请先在 knowledge 目录添加政策文档。",
            "hits": [],
        }

    q_tokens = _tokenize(query)
    q_set = set(q_tokens)
    scored: List[tuple[int, Chunk]] = []
    for c in chunks:
        c_tokens = _tokenize(c.text)
        overlap = len(q_set.intersection(c_tokens))
        if overlap > 0:
            scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    hits = scored[: max(1, top_k)]
    if not hits:
        return {
            "answer": "未命中明确政策片段，请换个问法或补充知识库文档。",
            "hits": [],
        }

    snippets = []
    for score, chunk in hits:
        snippets.append(
            {
                "source": chunk.source,
                "score": score,
                "snippet": chunk.text[:260],
            }
        )
    summary = "；".join([f"参考 {h['source']}" for h in snippets])
    return {
        "answer": f"已检索到相关政策片段，{summary}。",
        "hits": snippets,
    }
