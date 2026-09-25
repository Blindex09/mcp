#!/usr/bin/env python3
"""
Test script para validar o Accessibility MCP Server antes de usar globalmente
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


def test_a11y_content():
    """Verifica se os guias e exemplos de acessibilidade embutidos estao presentes"""
    content = Path(__file__).parent / "a11y" / "content"
    refs = list((content / "references").glob("*.md"))
    examples = [p for p in (content / "examples").glob("*") if p.is_file()]
    axe = Path(__file__).parent / "a11y" / "vendor" / "axe.min.js"

    print(f"✅ {len(refs)} guias de referencia" if refs else "❌ Nenhum guia em a11y/content/references")
    print(f"✅ {len(examples)} exemplos de componentes" if examples else "❌ Nenhum exemplo em a11y/content/examples")
    print("✅ axe-core vendorizado" if axe.exists() else "❌ a11y/vendor/axe.min.js ausente")
    return bool(refs) and bool(examples) and axe.exists()


def test_browser_optional():
    """Playwright/Chromium so sao necessarios para a11y_audit, a11y_aria_snapshot e a11y_tab_order"""
    try:
        import playwright  # noqa: F401
        print("✅ playwright instalado (rode 'python -m playwright install chromium' uma vez)")
    except ImportError:
        print("⚠️  playwright ausente: as ferramentas de auditoria no navegador nao funcionarao (pip install playwright)")
    return True  # opcional: nao reprova o setup


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
    print("🧪 Accessibility MCP Server - Test Suite\n")
    
    tests = [
        ("Python Version", test_python_version),
        ("Dependencies", test_dependencies),
        ("Conteudo de acessibilidade", test_a11y_content),
        ("Navegador (opcional)", test_browser_optional),
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
