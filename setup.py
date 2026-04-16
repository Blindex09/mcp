#!/usr/bin/env python3
"""
Setup script para registrar o Skills MCP Server em Claude Desktop, VSCode e Cursor
"""

import json
import os
from pathlib import Path


def setup_claude_desktop():
    """Configura MCP Server para Claude Desktop"""
    
    # Caminho do config do Claude Desktop
    if os.name == 'nt':  # Windows
        config_path = Path(os.getenv('APPDATA')) / 'Claude' / 'claude_desktop_config.json'
    else:  # macOS/Linux
        config_path = Path.home() / 'Library' / 'Application Support' / 'Claude' / 'claude_desktop_config.json'
    
    # Garante que o diretório existe
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Carrega config existente
    config: dict = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"  ⚠️  Config existente mal-formado em {config_path} — sobrescrevendo.")
    
    # Garante mcpServers existe
    if 'mcpServers' not in config:
        config['mcpServers'] = {}
    
    # Adiciona/atualiza skills server
    config['mcpServers']['skills'] = {
        "command": "uv",
        "args": ["--directory", "c:/mcp", "run", "mcp_server.py"]
    }
    
    # Salva
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Claude Desktop configurado em: {config_path}")


def setup_cursor():
    """Configura MCP Server para Cursor (global)"""
    
    config_path = Path.home() / '.cursor' / 'mcp.json'
    
    # Garante que o diretório existe
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Carrega config existente
    config: dict = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"  ⚠️  Config existente mal-formado em {config_path} — sobrescrevendo.")
    
    # Garante mcpServers existe
    if 'mcpServers' not in config:
        config['mcpServers'] = {}
    
    # Adiciona/atualiza skills server
    config['mcpServers']['skills'] = {
        "command": "uv",
        "args": ["--directory", "c:\\mcp", "run", "mcp_server.py"]
    }
    
    # Salva
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Cursor configurado em: {config_path}")


def setup_vscode():
    """Instruções para VSCode (configuração manual via settings.json)"""
    
    print("\n📝 Para VSCode, adicione à settings.json:")
    print("""
{
  "mcp.servers": {
    "skills": {
      "command": "uv",
      "args": ["--directory", "c:\\\\mcp", "run", "mcp_server.py"]
    }
  }
}
    """)


def main():
    print("🔧 MCP Skills Server - Setup Script\n")
    print("Registrando servidor MCP em todas as plataformas...\n")
    
    try:
        setup_claude_desktop()
        setup_cursor()
        setup_vscode()
        
        print("\n✅ Setup concluído!")
        print("\n⚠️  Próximos passos:")
        print("1. Reinicie Claude Desktop")
        print("2. Reinicie Cursor")
        print("3. Reinicie VSCode")
        print("4. As skills estarão disponíveis como ferramentas MCP")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
