"""Conteudo decidido pelo cliente; contratos objetivos para documentos acessiveis."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import wcag


class Block(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["paragraph", "heading", "list", "table", "image", "link", "field"]
    id: str = Field(default="", pattern=r"^(?:[A-Za-z][A-Za-z0-9_]{0,39})?$")
    text: str = ""
    level: int = Field(default=2, ge=2, le=6)
    items: list[str] = Field(default_factory=list)
    ordered: bool = False
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    source: str = ""
    alt: str = ""
    url: str = ""
    field_name: str = Field(default="", pattern=r"^(?:[A-Za-z][A-Za-z0-9_]{0,39})?$")
    field_type: Literal["text", "checkbox", "choice"] = "text"
    value: str = ""
    checked: bool = False
    required: bool = False
    help_text: str = ""
    options: list[str] = Field(default_factory=list)
    multiline: bool = False

    @model_validator(mode="after")
    def check_content(self) -> Block:
        if self.kind in ("paragraph", "heading", "link") and not self.text.strip():
            raise ValueError("Informe o texto do bloco.")
        if self.kind == "list" and (not self.items or any(not s.strip() for s in self.items)):
            raise ValueError("Uma lista precisa de itens nao vazios.")
        if self.kind == "table":
            if not self.text.strip() or not self.headers or any(not h.strip() for h in self.headers):
                raise ValueError("Uma tabela precisa de legenda (text) e cabecalhos nao vazios.")
            if not self.rows or any(len(row) != len(self.headers) for row in self.rows):
                raise ValueError("Cada linha deve ter uma celula por cabecalho.")
        if self.kind == "image" and (not self.source or not self.alt.strip()):
            raise ValueError("Uma imagem precisa de caminho local (source) e texto alternativo (alt).")
        if self.kind == "link":
            parsed = urlsplit(self.url)
            valid = parsed.scheme in ("http", "https") and bool(parsed.netloc)
            valid = valid or (parsed.scheme == "mailto" and bool(parsed.path))
            valid = valid or (self.url.startswith("#") and bool(self.url[1:]))
            if not valid:
                raise ValueError("Link deve usar http, https, mailto ou um destino interno #id.")
        if self.id and self.kind != "heading":
            raise ValueError("id identifica somente titulos de destino.")
        if self.kind == "field":
            if not self.field_name or not self.text.strip() or not self.help_text.strip():
                raise ValueError("Campo exige field_name, text como rotulo e help_text como instrucao.")
            if self.field_type == "choice":
                if not self.options or any(not option.strip() for option in self.options) or len(set(self.options)) != len(self.options):
                    raise ValueError("Escolha exige opcoes distintas e nao vazias.")
                if self.value and self.value not in self.options:
                    raise ValueError("O valor deve pertencer as opcoes da escolha.")
            elif self.options:
                raise ValueError("options pertence somente a campos choice.")
            if self.multiline and self.field_type != "text":
                raise ValueError("multiline pertence somente a campos text.")
            if self.field_type == "checkbox" and self.value:
                raise ValueError("Use checked para o estado de uma caixa de selecao.")
        return self


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion: str
    status: Literal["Supports", "Partially Supports", "Does Not Support", "Not Applicable", "Not Evaluated"]
    coverage: Literal["complete", "partial", "not_evaluated"] = "not_evaluated"
    evidence: list[str] = Field(default_factory=list)
    remarks: str = Field(min_length=1)

    @model_validator(mode="after")
    def check_evidence(self) -> Assessment:
        if not self.remarks.strip() or any(not item.strip() for item in self.evidence):
            raise ValueError("Justificativa e evidencias nao podem conter somente espacos.")
        if self.criterion not in wcag.CRITERIA:
            raise ValueError("Criterio WCAG inexistente.")
        if self.status != "Not Evaluated" and not any(s.strip() for s in self.evidence):
            raise ValueError("Conclusao de conformidade precisa de evidencia explicita.")
        if self.status != "Not Evaluated" and self.coverage != "complete":
            raise ValueError("Conclusao exige cobertura completa declarada pelo avaliador; avaliacao incompleta permanece Not Evaluated.")
        return self


class DocumentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    language: str = Field(default="pt-BR", pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
    author: str = ""
    subject: str = ""
    toc: bool = False
    blocks: list[Block] = Field(min_length=1)
    assessments: list[Assessment] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_outline(self) -> DocumentSpec:
        if not self.title.strip():
            raise ValueError("O titulo nao pode estar vazio.")
        previous = 1
        for block in self.blocks:
            if block.kind == "heading":
                if block.level > previous + 1:
                    raise ValueError("A hierarquia de titulos nao pode pular niveis; o titulo do documento e o nivel 1.")
                previous = block.level
        ids = [a.criterion for a in self.assessments]
        if len(ids) != len(set(ids)):
            raise ValueError("Um criterio nao pode ter duas conclusoes no mesmo documento.")
        headings = [block.id or f"sec_{index}" for index, block in enumerate(self.blocks, 1) if block.kind == "heading"]
        if len(set(headings)) != len(headings) or "document_title" in headings:
            raise ValueError("Destinos de titulos devem ser unicos; document_title e reservado.")
        for block in self.blocks:
            if block.kind == "link" and block.url.startswith("#") and block.url[1:] not in {"document_title", *headings}:
                raise ValueError("O destino interno do link nao existe neste documento.")
        names = [block.field_name for block in self.blocks if block.kind == "field"]
        if len(set(names)) != len(names):
            raise ValueError("Nomes de campos devem ser unicos.")
        if set(names) & {"document_title", *headings}:
            raise ValueError("Campos e destinos internos devem ter identificadores distintos.")
        if self.toc and not headings:
            raise ValueError("O sumario precisa de pelo menos um titulo de secao.")
        return self
