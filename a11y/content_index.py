"""Indice (BM25) sobre as referencias e exemplos de acessibilidade embutidos.

Toda leitura passa por nomes do indice - o texto vindo do cliente nunca vira
caminho de arquivo, entao nao ha como sair da pasta de conteudo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONTENT_DIR = Path(__file__).parent / "content"
_TOKEN = re.compile(r"[a-z0-9]+")
_EXAMPLE_EXTS = {".html", ".js", ".ts", ".tsx", ".jsx", ".css", ".kt", ".swift", ".vue", ".svelte"}


@dataclass(frozen=True)
class Chunk:
    kind: str  # "reference" | "example" | "skill"
    name: str  # nome do arquivo (sem extensao)
    heading: str
    text: str


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _split_markdown(text: str) -> list[tuple[str, str]]:
    """Divide em (titulo, corpo) a cada cabecalho # ou ##."""
    parts: list[tuple[str, str]] = []
    heading = "(inicio)"
    buf: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#{1,2}\s", line):
            if buf:
                parts.append((heading, "\n".join(buf)))
            heading, buf = line.lstrip("# ").strip(), []
        else:
            buf.append(line)
    if buf:
        parts.append((heading, "\n".join(buf)))
    return [(h, b) for h, b in parts if b.strip()]


class ContentIndex:
    def __init__(self, root: Path = CONTENT_DIR) -> None:
        self.root = root
        self.references: dict[str, Path] = {}
        self.examples: dict[str, Path] = {}
        self.chunks: list[Chunk] = []
        self._bm25: Any = None
        self._load()

    def _load(self) -> None:
        ref_dir = self.root / "references"
        if ref_dir.is_dir():
            for p in sorted(ref_dir.glob("*.md")):
                self.references[p.stem] = p
                for heading, body in _split_markdown(p.read_text(encoding="utf-8", errors="replace")):
                    self.chunks.append(Chunk("reference", p.stem, heading, body))
        ex_dir = self.root / "examples"
        if ex_dir.is_dir():
            for p in sorted(ex_dir.iterdir()):
                if p.is_file() and p.suffix in _EXAMPLE_EXTS:
                    self.examples[p.stem] = p
                    text = p.read_text(encoding="utf-8", errors="replace")
                    self.chunks.append(Chunk("example", p.stem, p.name, text[:3000]))
        skill = self.root / "SKILL.md"
        if skill.is_file():
            for heading, body in _split_markdown(skill.read_text(encoding="utf-8", errors="replace")):
                self.chunks.append(Chunk("skill", "SKILL", heading, body))
        if self.chunks:
            from rank_bm25 import BM25Okapi

            self._bm25 = BM25Okapi(
                [_tokens(f"{c.name} {c.heading} {c.heading} {c.text}") for c in self.chunks]
            )

    def search(self, query: str, kind: str = "all", top_k: int = 8) -> list[tuple[float, Chunk]]:
        q = _tokens(query)
        if not q or self._bm25 is None:
            return []
        scores = self._bm25.get_scores(q)
        ranked = sorted(zip(scores, self.chunks), key=lambda x: -x[0])
        out: list[tuple[float, Chunk]] = []
        for score, chunk in ranked:
            if score <= 0:
                break
            if kind != "all" and chunk.kind != kind:
                continue
            out.append((float(score), chunk))
            if len(out) >= max(1, min(top_k, 30)):
                break
        return out

    def read(self, kind: str, name: str) -> str | None:
        table = self.references if kind == "reference" else self.examples
        key = name.strip()
        for ext in (".md", *_EXAMPLE_EXTS):
            if key.endswith(ext):
                key = key[: -len(ext)]
                break
        path = table.get(key)
        return path.read_text(encoding="utf-8", errors="replace") if path else None
