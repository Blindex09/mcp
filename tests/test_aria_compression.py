"""Testes unitarios da compressao deterministica de snapshots ARIA."""

from accessibility_mcp.a11y.aria_compression import compress_aria_snapshot


def test_small_snapshot_is_not_modified():
    yaml = "- main:\n" + "\n".join(f'  - text "Linha {i}"' for i in range(40))
    out, removed = compress_aria_snapshot(yaml)
    assert out == yaml and removed == 0


def test_large_repetitive_non_interactive_siblings_collapse_keeping_ten():
    items = "\n".join(f'    - listitem "Item {i}"' for i in range(130))
    yaml = f'- main:\n  - heading "Lista" [level=1]\n  - list:\n{items}\n  - button "Enviar"'
    out, removed = compress_aria_snapshot(yaml)
    assert removed > 100
    assert 'heading "Lista"' in out
    assert 'button "Enviar"' in out
    assert 'listitem "Item 0"' in out
    assert 'listitem "Item 9"' in out
    assert 'listitem "Item 10"' not in out
    assert "compressor" in out or "compressao" in out


def test_interactive_siblings_are_never_collapsed():
    buttons = "\n".join(f'  - button "Acao {i}"' for i in range(130))
    yaml = f"- main:\n{buttons}"
    out, removed = compress_aria_snapshot(yaml)
    assert out == yaml and removed == 0
