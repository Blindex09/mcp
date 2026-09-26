"""Varredura de varias paginas: descoberta (sitemap + links), robots.txt, so GET, fatos consolidados."""
import http.server
import json
import threading
from typing import ClassVar

import pytest

from a11y import crawl as crawl_mod
from a11y.crawl import crawl

PAGES = {
    "/": "<html lang='pt'><title>Home</title><body><main><h1>Home</h1><a href='/a'>A</a><a href='/b'>B</a><a href='/private/x'>Privado</a>"
         "<a href='https://outro-site.example/'>Fora</a><a href='/arquivo.pdf'>PDF</a><img src='x.png'></main></body></html>",
    "/a": "<html lang='pt'><title>Pagina</title><body><main><h1>A</h1><h3>pulou</h3><a href='/c'>C</a><input name='q'></main></body></html>",
    "/b": "<html><title>Pagina</title><body><main><h1>B</h1><h1>B de novo</h1><button></button></main></body></html>",
    "/c": "<html lang='pt'><title>C</title><body><main><p>sem h1</p></main></body></html>",
    "/d": "<html lang='pt'><title>So no sitemap</title><body><main><h1>D</h1></main></body></html>",
    "/private/x": "<html lang='pt'><title>Privado</title><body><h1>NAO DEVE SER VISITADO</h1></body></html>",
}


class Site(http.server.BaseHTTPRequestHandler):
    hits: ClassVar[list[tuple[str, str]]] = []

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        Site.hits.append((self.command, self.path))
        if self.path == "/robots.txt":
            self._send(200, "text/plain", "User-agent: *\nDisallow: /private/\n")
        elif self.path == "/sitemap.xml":
            host = self.headers["Host"]
            self._send(200, "application/xml", f"<urlset><url><loc>http://{host}/d</loc></url></urlset>")
        elif self.path == "/arquivo.pdf":
            self._send(200, "application/pdf", "%PDF-1.4")
        elif self.path in PAGES:
            self._send(200, "text/html", PAGES[self.path])
        else:
            self._send(404, "text/plain", "nao existe")

    do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = do_GET  # qualquer metodo fica registrado

    def log_message(self, *args, **kwargs):
        return


@pytest.fixture()
def site(monkeypatch):
    Site.hits = []
    monkeypatch.setattr(crawl_mod, "POLITE_PAUSE_S", 0)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


async def test_crawl_discovers_by_links_and_sitemap_respects_robots_and_stays_on_site(site):
    r = await crawl(site + "/", max_pages=10)
    visited = {p["url"].replace(site, "") for p in r["pages"]}
    assert visited == {"/", "/a", "/b", "/c", "/d"}  # /d so existe no sitemap; /c so por link de /a
    assert [u.replace(site, "") for u in r["skipped"]["robots_disallowed"]] == ["/private/x"]
    assert not any(path == "/private/x" for _, path in Site.hits)  # o robots foi obedecido de verdade
    assert [u.replace(site, "") for u in r["skipped"]["not_html"]] == ["/arquivo.pdf"]
    assert all("outro-site" not in p["url"] for p in r["pages"])  # nunca sai do site
    assert {m for m, _ in Site.hits} <= {"GET", "HEAD"}  # so leitura (HEAD so verifica o tipo de conteudo)


async def test_crawl_consolidates_facts_without_judgment(site):
    r = await crawl(site + "/", max_pages=10)
    f = r["site_facts"]
    assert f["duplicate_titles"][0]["title"] == "Pagina" and f["duplicate_titles"][0]["pages"] == 2
    assert [u.replace(site, "") for u in f["pages_without_lang"]] == ["/b"]
    assert [u.replace(site, "") for u in f["pages_without_h1"]] == ["/c"]
    assert [u.replace(site, "") for u in f["pages_with_several_h1"]] == ["/b"]
    assert [u.replace(site, "") for u in f["pages_with_heading_jumps"]] == ["/a"]
    assert f["images_without_alt_attr_total"] == 1 and f["fields_without_name_total"] == 1
    assert "html-has-lang" in f["axe_rules_by_pages"] and "button-name" in f["axe_rules_by_pages"]
    home = next(p for p in r["pages"] if p["url"].rstrip("/") == site)
    assert home["title"] == "Home" and home["status"] == 200
    text = json.dumps(r)
    assert "veredito" not in text and "verdict" not in text


async def test_crawl_respects_the_page_limit_and_reports_what_was_left(site):
    r = await crawl(site + "/", max_pages=2)
    assert r["pages_visited"] == 2 and r["not_visited"] > 0 and r["urls_discovered"] > 2


async def test_crawl_validates_input():
    with pytest.raises(ValueError):
        await crawl("file:///c:/windows/win.ini")
    with pytest.raises(ValueError):
        await crawl("http://127.0.0.1:1/", level="ZZ")


async def test_crawl_tool_returns_json(site):
    import mcp_server

    out = json.loads(await mcp_server.mcp._tool_manager.get_tool("a11y_crawl").fn(url=site + "/", max_pages=3))
    assert out["pages_visited"] == 3 and "site_facts" in out
    bad = json.loads(await mcp_server.mcp._tool_manager.get_tool("a11y_crawl").fn(url="ftp://x/"))
    assert "error" in bad
