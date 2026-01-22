import os
import re


def _read(repo_root: str, rel_path: str) -> str:
    p = os.path.join(repo_root, rel_path)
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def test_frontend_has_first_load_modal_and_onboarding_keys():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    content = _read(repo_root, "frontend/main.js")
    assert "function showFirstLoadModal" in content
    assert "ms_intro_modal_v1" in content
    assert "ms_onboarding_v1" in content


def test_frontend_has_furious_glow_css_and_modal_css():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    css = _read(repo_root, "frontend/css/style.css")
    assert "#sidebar-toggle.furious-glow" in css
    assert "@keyframes furiousGlow" in css
    assert ".ms-intro-backdrop" in css
    assert ".ms-intro-modal" in css


def test_frontend_stat_cards_have_tooltip_html():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    html = _read(repo_root, "frontend/index.html")
    # We expect 4 analytics cards with rich tooltip content
    assert html.count("data-tooltip-html=") >= 4
    assert "SAR Detections" in html
    assert "SAR matched to AIS" in html
    assert "Dark Traffic Clusters" in html


def test_frontend_tooltips_support_tap_toggle():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    js = _read(repo_root, "frontend/main.js")
    # Contract: tap-to-toggle uses a class and a click listener for closing
    assert "tooltip-open" in js
    assert "document.addEventListener('click', closeAll" in js


def test_docs_mirror_contains_modal_css_and_tooltips():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    docs_css = _read(repo_root, "docs/css/style.css")
    docs_html = _read(repo_root, "docs/index.html")
    docs_js = _read(repo_root, "docs/main.js")

    assert ".ms-intro-backdrop" in docs_css
    assert ".ms-intro-modal" in docs_css
    assert "#sidebar-toggle.furious-glow" in docs_css or "furiousGlow" in docs_css

    assert "data-tooltip-html=" in docs_html
    assert "SAR matched to AIS" in docs_html

    # Tooltip tap-toggle logic mirrored
    assert "tooltip-open" in docs_js
    assert "document.addEventListener('click', closeAll" in docs_js

