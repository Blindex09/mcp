"""Indice das referencias e exemplos de acessibilidade embutidos.

Toda leitura passa por nomes do indice - o texto vindo do cliente nunca vira
caminho de arquivo, entao nao ha como sair da pasta de conteudo.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

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

    def _manifest(self) -> dict[str, dict[str, str]]:
        """Descricoes escritas por IA (catalog.json), nao extraidas por regex."""
        try:
            data = json.loads((self.root / "catalog.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("catalog.json ausente ou invalido em %s", self.root)
            return {}
        return {k: v for k, v in data.items() if isinstance(v, dict)}

    def _items(self) -> list[tuple[str, str, Path]]:
        out: list[tuple[str, str, Path]] = []
        out += [("reference", n, p) for n, p in self.references.items()]
        out += [("example", n, p) for n, p in self.examples.items()]
        for name, path in self.templates.items():
            out.append(("script" if name.startswith("scripts/") else "template", name, path))
        return out

    def catalog_problems(self) -> dict[str, list[str]]:
        """Itens do disco sem descricao e descricoes de itens que nao existem mais (para o teste de consistencia)."""
        manifest = self._manifest()
        on_disk = {(k, n) for k, n, _ in self._items()}
        described = {(k, n) for k, group in manifest.items() for n in group}
        return {
            "sem_descricao": sorted(f"{k}:{n}" for k, n in on_disk - described),
            "descricao_orfa": sorted(f"{k}:{n}" for k, n in described - on_disk),
        }

    def catalog(self) -> list[dict[str, str]]:
        """Catalogo para o MODELO escolher: tipo, nome, quando usar (texto escrito por IA) e secoes reais do guia.

        Nada e resumido por regra: a descricao vem de catalog.json e as secoes sao os cabecalhos do proprio guia.
        Quem decide o que serve a uma tarefa e a IA, nunca uma regra de palavras-chave.
        """
        manifest = self._manifest()
        items: list[dict[str, str]] = []
        for kind, name, path in self._items():
            item = {"kind": kind, "name": name, "quando_usar": manifest.get(kind, {}).get(name, "(sem descricao no catalogo)")}
            if kind == "reference":
                heads = [h for h, _ in _split_markdown(path.read_text(encoding="utf-8", errors="replace"))][1:9]
                item["secoes"] = "; ".join(heads)
            items.append(item)
        return items
