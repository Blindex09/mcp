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


def test_catalog_describes_every_item_for_the_model(index):
    cat = index.catalog()
    assert len(cat) == len(index.references) + len(index.examples)
    ref = next(c for c in cat if c["name"] == "audit-checklist")
    assert ref["kind"] == "reference" and ref["summary"] and ref["sections"]


def test_no_keyword_ranking_left():
    import a11y.content_index as ci

    assert not hasattr(ci.ContentIndex, "search")


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
        "a11y_list_content", "a11y_find", "a11y_get_reference", "a11y_get_example",
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


async def test_find_falls_back_to_catalog_without_sampling():
    """Sem sampling no cliente, nada de palavra-chave: devolve o catalogo pro modelo escolher."""
    out = await mcp_server.mcp.call_tool("a11y_find", {"task": "preciso de um modal acessivel"})
    text = json.dumps(out, default=str)
    assert "unavailable" in text and "audit-checklist" in text


async def test_find_uses_model_choice_and_drops_invented_names(monkeypatch):
    from types import SimpleNamespace

    from mcp.types import TextContent

    from a11y import tools

    async def fake_create_message(**_kw):
        return SimpleNamespace(content=TextContent(type="text", text='["modal-native-dialog", "inventado"]'))

    fake_ctx = SimpleNamespace(session=SimpleNamespace(create_message=fake_create_message))
    fn = next(t for t in await mcp_server.mcp.list_tools() if t.name == "a11y_find")
    assert fn  # registrado
    tool = mcp_server.mcp._tool_manager.get_tool("a11y_find")
    out = await tool.fn(task="dialogo modal", ctx=fake_ctx)
    data = json.loads(out)
    assert data["selection"] == "model"
    assert [i["name"] for i in data["items"]] == ["modal-native-dialog"]
    assert tools.get_index().read("example", "modal-native-dialog")
