"""Testes unitarios deterministicos de ciencia de cores: CSS parsing, 0.04045, APCA, daltonismo e ajuste OKLCH."""

import math

import pytest

from accessibility_mcp.a11y import audit, color_science


def test_parse_color_accepts_hex_rgb_opaque_rgba_hsl_and_oklch():
    assert color_science.parse_color("#0a5") == (0, 170, 85)
    assert color_science.parse_color("#0b57d0") == (11, 87, 208)
    assert color_science.parse_color("rgb(11, 87, 208)") == (11, 87, 208)
    assert color_science.parse_color("rgb(100% 0% 50% / 1)") == (255, 0, 128)
    assert color_science.parse_color("rgba(11, 87, 208, 1)") == (11, 87, 208)
    assert color_science.parse_color("hsl(120, 100%, 50%)") == (0, 255, 0)
    assert color_science.parse_color("hsl(0.5turn 100% 50% / 100%)") == (0, 255, 255)
    oklch_white = color_science.parse_color("oklch(1 0 0)")
    assert oklch_white == (255, 255, 255)
    oklch_blue = color_science.parse_color("oklch(0.68 0.14 250)")
    assert oklch_blue[2] > oklch_blue[0]


@pytest.mark.parametrize(
    "bad",
    ["red", "rebeccapurple", "rgba(0, 0, 0, 0.5)", "rgb(0 0 0 / 50%)", "hsl(120 100% 50% / 0.2)", "oklch(0.5 -0.1 20)", "#12345"],
)
def test_parse_color_rejects_named_semitransparent_and_malformed(bad):
    with pytest.raises(ValueError):
        color_science.parse_color(bad)


def test_luminance_cutoff_004045_and_apca_known_references():
    assert math.isclose(color_science.srgb_to_linear(10), (10 / 255.0) / 12.92, rel_tol=1e-9)
    assert math.isclose(color_science.srgb_to_linear(11), ((11 / 255.0 + 0.055) / 1.055) ** 2.4, rel_tol=1e-9)
    assert color_science.apca_contrast((0, 0, 0), (255, 255, 255)) > 105.0
    assert color_science.apca_contrast((255, 255, 255), (0, 0, 0)) < -105.0
    assert color_science.apca_contrast((120, 120, 120), (120, 120, 120)) == 0.0


def test_cvd_simulation_covers_all_eight_types_and_preserves_gray():
    fg, bg = (200, 30, 30), (30, 150, 30)
    sim = color_science.cvd_contrast_report(fg, bg)
    assert set(sim) == set(color_science.CVD_TYPES) and len(sim) == 8
    sim_fg = color_science.parse_color(sim["deuteranopia"]["foreground"])
    sim_bg = color_science.parse_color(sim["deuteranopia"]["background"])
    assert color_science.delta_e_lab(sim_fg, sim_bg) < color_science.delta_e_lab(fg, bg) * 0.75
    red_on_white = color_science.wcag_contrast_ratio((220, 0, 0), (255, 255, 255))
    sim_red = color_science.cvd_contrast_report((220, 0, 0), (255, 255, 255))
    assert red_on_white >= 4.5 and sim_red["deuteranopia"]["ratio"] < 3.0
    achrom_fg = color_science.simulate_cvd((128, 128, 128), "protanopia")
    assert achrom_fg == (128, 128, 128)


def test_suggest_contrast_fix_finds_minimal_oklch_adjustment():
    rep = audit.contrast_report("#888888", "#ffffff", include_cvd=True)
    assert not rep["AA_text"]
    assert rep["suggested_aa_fix"] is not None
    assert rep["suggested_aa_fix"]["ratio"] >= 4.5
    assert rep["suggested_aa_fix"]["direction"] == "darker"
    assert rep["suggested_aaa_fix"] is not None
    assert rep["suggested_aaa_fix"]["ratio"] >= 7.0
    assert len(rep["cvd_simulation"]) == 8
    ok = audit.contrast_report("oklch(0.3 0.05 240)", "#ffffff")
    assert ok["AA_text"] and ok["suggested_aa_fix"] is None
