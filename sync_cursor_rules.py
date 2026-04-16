#!/usr/bin/env python3
"""
sync_cursor_rules.py
Sincroniza ~/.claude/CLAUDE.md → Cursor User Rules (aicontext.personalContext)

Uso:
    python c:/mcp/sync_cursor_rules.py          # sync silencioso
    python c:/mcp/sync_cursor_rules.py --show   # mostra o que será gravado
    python c:/mcp/sync_cursor_rules.py --clear  # limpa as rules do Cursor

ATENÇÃO: Feche o Cursor antes de executar para evitar conflito de banco.
"""

import sqlite3
import sys
import os
import re
from pathlib import Path

# Fix encoding para Windows (cp1252 nao suporta emojis)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
CURSOR_DB = Path.home() / "AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
KEY = "aicontext.personalContext"

# Seções do CLAUDE.md a incluir nas rules do Cursor (mais relevantes para coding)
SECTIONS_TO_INCLUDE = [
    "Como trabalhar comigo",
    "Regras Universais de Desenvolvimento",
    "TypeScript / Node.js",
    "Python",
    "React Native / Expo",
    "Supabase",
    "Git e Processo",
]

# Seções a excluir (muito longas ou irrelevantes para o Cursor)
SECTIONS_TO_EXCLUDE = [
    "Skills e Comandos Disponíveis",
    "Plugins Globais Ativos",
    "Ambiente",
    "Docker / WSL",
]


def extract_relevant_sections(content: str) -> str:
    """Extrai as seções mais relevantes do CLAUDE.md para o Cursor."""
    lines = content.split("\n")
    result_lines = []
    in_section = False
    skip_section = False
    current_section = ""

    for line in lines:
        # Detectar cabeçalho de seção (## ou ###)
        header_match = re.match(r"^#{1,3}\s+(.+)", line)
        if header_match:
            current_section = header_match.group(1).strip()
            # Remover emojis do título para comparação
            clean_section = re.sub(r"[^\w\s/()áéíóúãõâêôàç\-]", "", current_section).strip()

            skip_section = any(excl in clean_section for excl in SECTIONS_TO_EXCLUDE)
            in_section = any(incl in clean_section for incl in SECTIONS_TO_INCLUDE)

            if not skip_section:
                result_lines.append(line)
            continue

        if skip_section:
            continue

        result_lines.append(line)

    return "\n".join(result_lines)


def build_cursor_rules(claude_md_path: Path) -> str:
    """Constrói o texto das rules para o Cursor a partir do CLAUDE.md."""
    if not claude_md_path.exists():
        raise FileNotFoundError(f"CLAUDE.md não encontrado em: {claude_md_path}")

    content = claude_md_path.read_text(encoding="utf-8")
    relevant = extract_relevant_sections(content)

    # Cabeçalho informativo
    header = (
        "# Regras do Cursor — sincronizadas de ~/.claude/CLAUDE.md\n"
        "# Execute c:/mcp/sync_cursor_rules.py para atualizar\n\n"
    )

    return header + relevant


def is_cursor_running() -> bool:
    """Verifica se o Cursor está rodando (Windows)."""
    import subprocess
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Cursor.exe", "/NH"],
        capture_output=True, text=True
    )
    return "Cursor.exe" in result.stdout


def sync(show_only: bool = False, clear: bool = False) -> None:
    if not CURSOR_DB.exists():
        print(f"❌ Banco do Cursor não encontrado: {CURSOR_DB}")
        print("   Certifique-se que o Cursor está instalado e foi aberto ao menos uma vez.")
        sys.exit(1)

    if clear:
        text = ""
        print("🗑️  Limpando Cursor User Rules...")
    else:
        text = build_cursor_rules(CLAUDE_MD)
        char_count = len(text)
        print(f"📄 CLAUDE.md lido → {char_count} caracteres extraídos")

    if show_only:
        print("\n" + "=" * 60)
        print(text[:3000] + ("..." if len(text) > 3000 else ""))
        print("=" * 60)
        print("\n⚠️  Modo --show: nada foi gravado.")
        return

    if is_cursor_running():
        print("⚠️  AVISO: O Cursor parece estar rodando.")
        print("   Recomendo fechar o Cursor antes de sincronizar para evitar conflito.")
        answer = input("   Continuar mesmo assim? (s/N): ").strip().lower()
        if answer != "s":
            print("Abortado.")
            sys.exit(0)

    try:
        conn = sqlite3.connect(str(CURSOR_DB))
        cur = conn.cursor()

        # Verificar se a chave existe
        cur.execute("SELECT key FROM ItemTable WHERE key=?", (KEY,))
        exists = cur.fetchone()

        if exists:
            cur.execute("UPDATE ItemTable SET value=? WHERE key=?", (text, KEY))
        else:
            cur.execute("INSERT INTO ItemTable (key, value) VALUES (?, ?)", (KEY, text))

        conn.commit()
        conn.close()

        if clear:
            print("✅ Cursor User Rules limpas.")
        else:
            print(f"✅ Cursor User Rules atualizadas ({len(text)} chars)")
            print("   Reinicie o Cursor para ver as mudanças em Settings → Rules.")

    except sqlite3.OperationalError as e:
        print(f"❌ Erro ao acessar banco do Cursor: {e}")
        print("   Feche o Cursor completamente e tente novamente.")
        sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    show_only = "--show" in args
    clear = "--clear" in args
    sync(show_only=show_only, clear=clear)
