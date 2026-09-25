"""Indice das referencias e exemplos de acessibilidade embutidos.

Toda leitura passa por nomes do indice - o texto vindo do cliente nunca vira
caminho de arquivo, entao nao ha como sair da pasta de conteudo.
"""

from __future__ import annotations

import re
from pathlib import Path

CONTENT_DIR = Path(__file__).parent / "content"
_EXAMPLE_EXTS = {".html", ".js", ".ts", ".tsx", ".jsx", ".css", ".kt", ".swift", ".vue", ".svelte"}


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
        self.templates: dict[str, Path] = {}  # assets/ e scripts/, chave = caminho relativo
        self._load()

    def _load(self) -> None:
        ref_dir = self.root / "references"
        if ref_dir.is_dir():
            for p in sorted(ref_dir.glob("*.md")):
                self.references[p.stem] = p
        ex_dir = self.root / "examples"
        if ex_dir.is_dir():
            for p in sorted(ex_dir.iterdir()):
                if p.is_file() and p.suffix in _EXAMPLE_EXTS:
                    self.examples[p.stem] = p
        for sub in ("assets", "scripts"):
            base = self.root / sub
            if base.is_dir():
                for p in sorted(base.rglob("*")):
                    if p.is_file() and p.name != ".gitignore":
                        self.templates[p.relative_to(self.root).as_posix()] = p

    def read(self, kind: str, name: str) -> str | None:
        key = name.strip()
        if kind == "template":  # chave exata do indice (ex.: assets/accessible-ai-react/src/ai/turnReducer.js)
            path = self.templates.get(key.replace("\\", "/"))
            return path.read_text(encoding="utf-8", errors="replace") if path else None
        table = self.references if kind == "reference" else self.examples
        for ext in (".md", *_EXAMPLE_EXTS):
            if key.endswith(ext):
                key = key[: -len(ext)]
                break
        path = table.get(key)
        return path.read_text(encoding="utf-8", errors="replace") if path else None

    def catalog(self) -> list[dict[str, str]]:
        """Catalogo para o MODELO escolher: nome, tipo, resumo e secoes de cada item.

        Aqui so se extrai o que o arquivo ja diz (titulo, primeiro paragrafo, cabecalhos);
        quem decide o que serve a uma tarefa e a IA, nunca uma regra de palavras-chave.
        """
        items: list[dict[str, str]] = []
        for name, path in self.references.items():
            text = path.read_text(encoding="utf-8", errors="replace")
            heads = [h for h, _ in _split_markdown(text)][:12]
            items.append({"kind": "reference", "name": name, "summary": _first_paragraph(text), "sections": "; ".join(heads)})
        for name, path in self.examples.items():
            text = path.read_text(encoding="utf-8", errors="replace")
            items.append({"kind": "example", "name": name, "summary": f"{path.suffix} - " + _leading_comment(text), "sections": ""})
        for name, path in self.templates.items():
            text = path.read_text(encoding="utf-8", errors="replace")
            kind = "script" if name.startswith("scripts/") else "template"
            items.append({"kind": kind, "name": name, "summary": _leading_comment(text), "sections": ""})
        return items


def _first_paragraph(text: str, limit: int = 220) -> str:
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if b and not b.startswith("#"):
            return " ".join(b.split())[:limit]
    return ""


def _leading_comment(text: str, limit: int = 160) -> str:
    m = re.search(r"<!--(.*?)-->|/\*(.*?)\*/|^//(.*)$|<title>(.*?)</title>", text, re.DOTALL | re.MULTILINE)
    if not m:
        return ""
    return " ".join(next(g for g in m.groups() if g is not None).split())[:limit]
