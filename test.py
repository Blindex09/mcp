#!/usr/bin/env python3
"""
Test script para validar o Skills MCP Server antes de usar globalmente
"""

import sys
from pathlib import Path
import subprocess
import json


def test_python_version():
    """Verifica se Python 3.10+ está disponível"""
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ requerido. Você tem: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} OK")
    return True


def test_dependencies():
    """Verifica se as dependências estão instaladas"""
    required = ['mcp']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"✅ {pkg} instalado")
        except ImportError:
            missing.append(pkg)
            print(f"❌ {pkg} NÃO instalado")
    
    if missing:
        print(f"\n⚠️  Instale com: uv sync  (ou pip install {' '.join(missing)})")
        return False
    return True


def test_skills_discovery():
    """Testa se as skills podem ser descobertas"""
    skills_path = Path("c:/skills")
    
    if not skills_path.exists():
        print(f"❌ Pasta de skills não existe: {skills_path}")
        return False
    
    skill_dirs = [d for d in skills_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    skill_count = len(skill_dirs)
    
    skills_with_md = sum(1 for d in skill_dirs if (d / 'SKILL.md').exists())
    
    print(f"✅ Encontradas {skill_count} pastas de skills")
    print(f"✅ {skills_with_md} delas têm SKILL.md")
    
    if skills_with_md == 0:
        print("⚠️  Nenhuma skill com SKILL.md encontrada!")
        return False
    
    return True


def test_server_startup():
    """Testa se o servidor MCP consegue iniciar (timeout rápido)"""
    print("\n⏳ Testando inicialização do servidor...")
    
    try:
        import time
        pr = subprocess.Popen(
            [sys.executable, "c:\\mcp\\mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(1)
        pr.kill()
        pr.wait()
        print("✅ Servidor consegue iniciar")
        return True
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
        return False


def main():
    print("🧪 MCP Skills Server - Test Suite\n")
    
    tests = [
        ("Python Version", test_python_version),
        ("Dependencies", test_dependencies),
        ("Skills Discovery", test_skills_discovery),
        ("Server Startup", test_server_startup),
    ]
    
    results = []
    for name, test_fn in tests:
        print(f"\n📋 {name}...")
        result = test_fn()
        results.append((name, result))
    
    # Resumo
    print("\n" + "="*50)
    print("📊 RESUMO DOS TESTES\n")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n{'='*50}")
    print(f"Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 Tudo pronto! Execute: python c:\\mcp\\setup.py")
        return 0
    else:
        print("\n⚠️  Resolva os erros acima antes de continuar")
        return 1


if __name__ == "__main__":
    exit(main())
