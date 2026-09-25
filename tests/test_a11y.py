"""Testes das ferramentas de acessibilidade embutidas (a11y/)."""
import json

import pytest

import mcp_server
from a11y import audit
from a11y.content_index import ContentIndex

BAD_HTML = "<html><head><title>t</title></head><body><img src='x.png'><button></button></body></html>"
GOOD_HTML = (
    "<!doctype html><html lang='en'><head><title>ok</title></head>"
    "<body><main><h1>Oi</h1><button>Enviar</button><a href='#a'>Link</a></main></body></html>"
)


@pytest.fixture(scope="module")
def index() -> ContentIndex:
    return ContentIndex()


def test_index_loads_content(index):
    assert "audit-checklist" in index.references
    assert "modal-native-dialog" in index.examples
    assert len(index.chunks) > 100


def test_search_finds_relevant_reference(index):
    hits = index.search("NVDA screen reader testing", kind="reference")
    assert hits and any("nvda" in c.name for _, c in hits[:3])


def test_search_empty_and_bad_query(index):
    assert index.search("") == []
    assert index.search("zzzqqqxxx") == []


def test_read_is_name_only_no_path_traversal(index):
    assert index.read("reference", "../../mcp_server") is None
    assert index.read("reference", "..\\..\\pyproject") is None
    assert index.read("example", "/etc/passwd") is None
    assert index.read("reference", "audit-checklist.md")


def test_contrast_known_values():
    r = audit.contrast_report("#000", "#fff")
    assert r["ratio"] == 21.0 and r["AAA_text"]
    low = audit.contrast_report("#777777", "#ffffff")
    assert not low["AA_text"] and low["AA_ui_components"]
    assert audit.contrast_report("#777777", "#ffffff", size_px=24)["AA_text"]


def test_contrast_rejects_bad_color():
    with pytest.raises(ValueError):
        audit.contrast_report("red", "#fff")


@pytest.mark.parametrize(
    "url", ["file:///c:/secret.txt", "javascript:alert(1)", "chrome://settings", "ftp://x/y", "http://", "x"]
)
def test_validate_url_blocks_non_http(url):
    with pytest.raises(ValueError):
        audit.validate_url(url)


async def test_audit_requires_exactly_one_source():
    with pytest.raises(ValueError):
        await audit.run_axe(None, None)
    with pytest.raises(ValueError):
        await audit.run_axe("http://a.b", "<p>x</p>")


async def test_audit_rejects_bad_level():
    with pytest.raises(ValueError):
        await audit.run_axe(None, GOOD_HTML, "ZZ")


def test_summarize_axe_orders_by_impact():
    raw = {
        "violations": [
            {"id": "a", "impact": "minor", "nodes": [{}], "tags": ["wcag2a"]},
            {"id": "b", "impact": "critical", "nodes": [{}, {}], "tags": ["wcag2a", "cat.x"]},
        ],
        "passes": [1, 2, 3],
    }
    out = audit.summarize_axe(raw)
    assert [v["id"] for v in out["violations"]] == ["b", "a"]
    assert out["violations"][0]["occurrences"] == 2
    assert out["violations"][0]["wcag_tags"] == ["wcag2a"]
    assert out["passes"] == 3


async def test_tools_registered_on_server():
    names = {t.name for t in await mcp_server.mcp.list_tools()}
    assert {
        "a11y_list_content", "a11y_search", "a11y_get_reference", "a11y_get_example",
        "a11y_contrast", "a11y_audit", "a11y_aria_snapshot", "a11y_tab_order",
    } <= names


async def test_tool_get_reference_unknown_lists_available():
    out = await mcp_server.mcp.call_tool("a11y_get_reference", {"name": "../nope"})
    assert "nao encontrada" in json.dumps(out, default=str)


async def test_tool_audit_url_scheme_blocked():
    out = await mcp_server.mcp.call_tool("a11y_audit", {"url": "file:///c:/windows/win.ini"})
    assert "http" in json.dumps(out, default=str)


@pytest.mark.slow
async def test_audit_real_browser_finds_violations_and_passes_clean_page():
    bad = await audit.run_axe(html=BAD_HTML)
    ids = {v["id"] for v in bad["violations"]}
    assert {"image-alt", "button-name"} <= ids
    good = await audit.run_axe(html=GOOD_HTML)
    assert good["violations"] == []


@pytest.mark.slow
async def test_tab_order_and_aria_snapshot_real_browser():
    order = await audit.tab_order(html=GOOD_HTML)
    assert [s["element"]["tag"] for s in order] == ["button", "a"]
    tree = await audit.aria_snapshot(html=GOOD_HTML)
    assert "button" in tree and "Enviar" in tree
