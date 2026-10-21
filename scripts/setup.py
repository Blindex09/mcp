#!/usr/bin/env python3
"""Registra o Accessibility MCP Server nos clientes MCP: Claude Desktop, Claude Code, Codex, Cursor e VS Code.

O servidor nao chama modelo e nao precisa de chave: o modelo e' o do cliente. Formatos conferidos nas paginas oficiais em 2026-10-19:
- Claude Code: `claude mcp add --transport stdio --scope user <nome> -- <comando> [args]` (code.claude.com/docs/en/mcp);
- Codex: `codex mcp add <nome> -- <comando> [args]`, que grava [mcp_servers.<nome>] em ~/.codex/config.toml (learn.chatgpt.com/docs/extend/mcp);
- VS Code: "MCP: Add Server" > Command (stdio), ou um mcp.json com a chave "servers" (code.visualstudio.com/docs/copilot/customization/mcp-servers).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOME = "accessibility"
LAUNCH = ["uv", "--directory", str(ROOT), "run", "mcp_server.py"]


def cli_add_command(cliente: str) -> list[str]:
    """O comando que cadastra o servidor num cliente de linha de comando (claude ou codex)."""
    if cliente == "claude":
        return ["claude", "mcp", "add", "--transport", "stdio", "--scope", "user", NOME, "--", *LAUNCH]
    if cliente == "codex":
        return ["codex", "mcp", "add", NOME, "--", *LAUNCH]
    raise ValueError(f"cliente desconhecido: {cliente}")


def vscode_json() -> str:
    """O trecho de mcp.json do VS Code (chave 'servers')."""
    return json.dumps({"servers": {NOME: {"type": "stdio", "command": LAUNCH[0], "args": LAUNCH[1:]}}}, indent=2, ensure_ascii=False)


def _merge_mcp_servers(config_path: Path, label: str) -> None:
    """Claude Desktop e Cursor usam a chave mcpServers num JSON: acrescenta/atualiza a entrada sem apagar as outras."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config: dict = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"    Config existente mal-formado em {config_path}: sobrescrevendo.")
    servers = config.setdefault("mcpServers", {})
    legacy = servers.get("skills")  # servidor antigo de skills do mesmo diretorio, substituido por este
    if legacy and "mcp" in json.dumps(legacy).lower():
        del servers["skills"]
    servers[NOME] = {"command": LAUNCH[0], "args": LAUNCH[1:]}
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f" {label} configurado em: {config_path}")


def setup_claude_desktop() -> None:
    if os.name == "nt":
        # o app instalado pela loja guarda a configuracao em LOCALAPPDATA\Claude-Data\<pasta do pacote>; o instalador comum, em APPDATA\Claude
        achados = sorted((Path(os.getenv("LOCALAPPDATA", "")) / "Claude-Data").glob("*/claude_desktop_config.json"))
        comum = Path(os.getenv("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
        if comum.exists() or not achados:
            achados.append(comum)
        for arquivo in achados:
            _merge_mcp_servers(arquivo, "Claude Desktop")
        return
    base = Path.home() / "Library" / "Application Support" / "Claude" if sys.platform == "darwin" else Path.home() / ".config" / "Claude"
    _merge_mcp_servers(base / "claude_desktop_config.json", "Claude Desktop")


def setup_cursor() -> None:
    _merge_mcp_servers(Path.home() / ".cursor" / "mcp.json", "Cursor")


def _already_registered(cliente: str) -> bool:
    try:
        out = subprocess.run([cliente, "mcp", "list"], capture_output=True, text=True, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return NOME in (out.stdout or "")


def require_codex_server(config_path: Path) -> bool:
    """Espera a inicializacao deste servidor antes de construir o catalogo inicial do Codex.

    O padrao de servidores opcionais pode entregar o primeiro turno sem ferramentas.
    Muda somente a chave required desta entrada; nao muda aprovacoes nem outros servidores.
    """
    if not config_path.is_file():
        return False
    text = config_path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^\[mcp_servers\.(?:accessibility|"accessibility")\][ \t]*\r?$', text)
    if match is None:
        return False
    following = re.search(r"(?m)^\[", text[match.end():])
    end = match.end() + following.start() if following else len(text)
    section = text[match.end():end]
    required = re.search(r"(?m)^required\s*=.*$", section)
    if required:
        section = section[:required.start()] + "required = true" + section[required.end():]
    else:
        section = "\nrequired = true" + section
    changed = text[:match.end()] + section + text[end:]
    if changed != text:
        config_path.write_text(changed, encoding="utf-8")
    return True


def setup_cli(cliente: str, nome_humano: str) -> None:
    """Claude Code e Codex: usa o proprio comando do cliente (escreve no arquivo certo, na versao certa)."""
    if not shutil.which(cliente):
        print(f" {nome_humano}: o comando `{cliente}` nao esta no PATH; para cadastrar depois, rode:\n    {' '.join(cli_add_command(cliente))}")
        return
    if _already_registered(cliente):
        if cliente == "codex":
            require_codex_server(Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml")
        print(f" {nome_humano}: a entrada '{NOME}' ja existe (nada a fazer).")
        return
    r = subprocess.run(cli_add_command(cliente), capture_output=True, text=True, check=False)
    if r.returncode == 0:
        if cliente == "codex":
            require_codex_server(Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml")
        print(f" {nome_humano} configurado (entrada '{NOME}').")
    else:
        print(f" {nome_humano}: nao deu para cadastrar sozinho ({(r.stderr or r.stdout).strip()[:200]}). Rode:\n    {' '.join(cli_add_command(cliente))}")


def setup_vscode() -> None:
    print(
        "\n VS Code: abra a paleta de comandos, rode `MCP: Add Server`, escolha `Command (stdio)`, digite o comando abaixo e o nome `accessibility`.\n"
        f"    {' '.join(LAUNCH)}\n"
        " Ou, num arquivo mcp.json (chave `servers`):\n" + "\n".join("    " + linha for linha in vscode_json().splitlines())
    )


def main() -> int:
    print(" Accessibility MCP Server - cadastro nos clientes (o servidor nao chama modelo: o modelo e' o do seu cliente)\n")
    try:
        setup_claude_desktop()
        setup_cli("claude", "Claude Code")
        setup_cli("codex", "Codex")
        setup_cursor()
        setup_vscode()
    except (OSError, ValueError) as e:
        print(f" Erro: {e}")
        return 1
    print("\n Proximos passos: reinicie o cliente que voce usa. No Claude Code, os fluxos prontos aparecem como /mcp__accessibility__a11y_review etc.;")
    print(" no VS Code como /accessibility.a11y_review; em qualquer cliente, a ferramenta a11y_workflow entrega o mesmo texto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
