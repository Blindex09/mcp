"""Documentos reais da galeria, conhecimento compartilhado e interface por teclado."""
import importlib.util
import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from accessibility_mcp.a11y import audit
from accessibility_mcp.a11y.content_index import ContentIndex
from accessibility_mcp.a11y.document_validation import validate
from accessibility_mcp.a11y.session import SESSION

DEMO = Path(__file__).resolve().parent.parent / "demo/exemplos-leitor-de-tela"
sys.path.insert(0, str(DEMO))
spec = importlib.util.spec_from_file_location("document_gallery", DEMO / "documentos.py")
assert spec and spec.loader
gallery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gallery)


def test_knowledge_and_site_follow_the_same_reviewed_contracts():
    assert gallery.GUIDE.read_text(encoding="utf-8") == gallery.guide_text()
    index = ContentIndex()
    assert not any(index.catalog_problems().values())
    assert "document-behavior-matrix" in index.references
    text = index.read("reference", "document-behavior-matrix")
    assert text and "a11y_create_document" in text and "a11y_nvda_speech" in text
    html = (DEMO / "documentos.html").read_text(encoding="utf-8")
    for item in gallery.DATA["scenarios"]:
        assert item["do"] in html and item["dont"] in html
        for source in item["sources"]:
            assert gallery.DATA["sources"][source]["url"] in html


@pytest.mark.parametrize("item", gallery.DATA["scenarios"], ids=lambda s: s["id"])
async def test_real_good_and_bad_files_preserve_the_documented_difference(item):
    root = DEMO / "documentos"
    for fmt in item["formats"]:
        good, bad = (root / f'{item["id"]}-{kind}.{fmt}' for kind in ("bom", "ruim"))
        good_check, bad_check = await validate(good, external=False), await validate(bad, external=False)
        assert good_check["status"] == "automated_checks_passed"
        assert good_check["conformance"] == bad_check["conformance"] == "not_determined"
        if item["detected"]:
            assert item["detected"] in {issue["code"] for issue in bad_check["issues"]}
        if item["id"] == "listas":
            assert gallery.structural_facts(good)["list_items"] == 2
            assert gallery.structural_facts(bad)["list_items"] == 0
        if item["id"] == "links":
            if fmt == "docx":
                assert "Clique aqui" in " ".join(gallery.structural_facts(bad)["link_text"])
            else:
                from pypdf import PdfReader
                assert "Clique aqui" in PdfReader(bad).pages[0].extract_text()
        if item["id"] == "ordem":
            first = gallery.structural_facts(good)["list_order_mcids"][0]
            second = gallery.structural_facts(bad)["list_order_mcids"][0]
            assert len(first) == 2 and first == list(reversed(second)) and first != second


def test_all_generated_pages_link_to_the_gallery_without_losing_content():
    from construir import CENARIOS

    for slug in ("index", "documentos", *(item["slug"] for item in CENARIOS)):
        html = (DEMO / f"{slug}.html").read_text(encoding="utf-8")
        assert 'href="documentos.html"' in html
        assert html.count('<main id="conteudo"') == 1
        assert html.count("</main>") == 1


def test_measurements_disclose_missing_speech_and_semantic_checks():
    data = json.loads((DEMO / "documentos/medicoes.json").read_text(encoding="utf-8"))
    assert data["nvda"].startswith("Não executado")
    for item in gallery.DATA["scenarios"]:
        for output in data["cases"][item["id"]]:
            assert output["bytes"] == (DEMO / "documentos" / output["file"]).stat().st_size
            assert output["validation"]["complete_validation"] is False
            if output["kind"] == "bom" and output["format"] == "pdf":
                assert output["validation"]["pdf_ua"]["status"] == "passed"
    html = (DEMO / "documentos.html").read_text(encoding="utf-8")
    assert "Este resultado não detecta nem aprova o defeito demonstrado" in html


async def test_gallery_can_be_used_by_keyboard_and_downloads_real_files():
    handler = partial(SimpleHTTPRequestHandler, directory=str(DEMO))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/documentos.html"
    await SESSION.open(url, None, "keyboard")
    download_context = None
    try:
        page = SESSION.page
        assert page
        assert await page.locator("h1").inner_text() == "Documentos acessíveis"
        result = await audit.run_axe(url=url)
        assert result["violations"] == []
        # O MCP bloqueia downloads por seguranca. O navegador de teste separado
        # aceita somente os arquivos locais desta galeria, sem mudar essa protecao.
        download_context = await SESSION.browser.new_context(accept_downloads=True)
        page = await download_context.new_page()
        await page.goto(url)
        downloads = page.locator("a[download]")
        assert await downloads.count() == 30
        # Percurso real do teclado, sem atribuir foco diretamente ao link.
        reached = set()
        for _ in range(await page.locator("a, summary").count() + 2):
            await page.keyboard.press("Tab")
            name = await page.evaluate("() => document.activeElement.getAttribute('href')")
            if name and name.startswith("documentos/") and not name.endswith(".json"):
                reached.add(name)
                if len(reached) == 1:
                    async with page.expect_download() as pending:
                        await page.keyboard.press("Enter")
                    download = await pending.value
                    path = await download.path()
                    assert Path(path).read_bytes() == (DEMO / name).read_bytes()
        assert len(reached) == 30
        await page.set_viewport_size({"width": 320, "height": 720})
        assert await page.evaluate("() => document.documentElement.scrollWidth <= innerWidth")
    finally:
        if download_context:
            await download_context.close()
        await SESSION.close()
        server.shutdown()
        server.server_close()
        thread.join()
