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


def test_no_toast_popups_only_console_logging():
    """
    UX contract: we do not show toast/pop-up messages for success/error.
    The helpers must log to console only (and keep their signatures).
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    fe_utils = _read(repo_root, "frontend/utils.js")
    docs_utils = _read(repo_root, "docs/utils.js")

    # No DOM creation for toasts
    assert "success-message" not in fe_utils
    assert "error-message" not in fe_utils
    assert "success-message" not in docs_utils
    assert "error-message" not in docs_utils

    # Console-only behavior
    assert "console.info" in fe_utils
    assert "console.error" in fe_utils
    assert "console.info" in docs_utils
    assert "console.error" in docs_utils


def test_stats_grid_is_2x2_including_mobile():
    """
    UX contract: analytics stat cards are a 2x2 block on mobile too.
    We assert both the base rule and any overrides use repeat(2, ...).
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _assert_two_cols(css: str) -> None:
        # Base .stats-grid rule
        base = re.search(r"\.stats-grid\s*\{[^}]*\}", css, flags=re.DOTALL)
        assert base, "Expected a .stats-grid rule"
        assert "grid-template-columns" in base.group(0)
        assert "repeat(2" in base.group(0)

        # Overlay-specific rule(s) (can appear in base + media query overrides)
        overlays = re.findall(r"#summary-stats\.map-analytics-overlay\s+\.stats-grid\s*\{[^}]*\}", css, flags=re.DOTALL)
        assert overlays, "Expected #summary-stats.map-analytics-overlay .stats-grid rule(s)"
        for block in overlays:
            assert "repeat(2" in block
            assert "repeat(3" not in block

    _assert_two_cols(_read(repo_root, "frontend/css/style.css"))
    _assert_two_cols(_read(repo_root, "docs/css/style.css"))


def test_stat_tooltips_are_viewport_clamped_and_body_rendered():
    """
    UX contract: stat-card tooltips should never bleed off-screen.
    Implementation contract:
      - tooltip divs are appended to document.body (so transforms don't break positioning)
      - CSS uses a global .custom-tooltip selector (not only as a child of .stat-card)
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    fe_js = _read(repo_root, "frontend/main.js")
    docs_js = _read(repo_root, "docs/main.js")
    fe_css = _read(repo_root, "frontend/css/style.css")
    docs_css = _read(repo_root, "docs/css/style.css")

    # JS: body append + clamped positioning
    for js in (fe_js, docs_js):
        assert "document.body.appendChild(tooltipDiv)" in js
        assert "Math.max" in js and "Math.min" in js  # clamp logic exists
        assert "positionTooltip" in js

    # CSS: global tooltip class exists (and the old scoped selector is gone)
    assert ".custom-tooltip {" in fe_css
    assert ".custom-tooltip {" in docs_css
    assert "stat-card[data-tooltip-html] .custom-tooltip" not in fe_css
    assert "stat-card[data-tooltip-html] .custom-tooltip" not in docs_css


def test_about_container_stretches_with_open_children():
    """
    UX contract: when #about-container is open, it should stretch with its accordion children.
    (No internal max-height clamp on the container/content, aside from the collapsed state.)
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    css = _read(repo_root, "frontend/css/style.css")

    about = re.search(r"#about-container\s*\{[^}]*\}", css, flags=re.DOTALL)
    assert about, "Expected #about-container rule"
    assert "max-height: none" in about.group(0)

    # Match the standalone rule, not the collapsed selector
    content = re.search(r"(?m)^\s*\.about-accordion-content\s*\{[^}]*\}", css, flags=re.DOTALL)
    assert content, "Expected standalone .about-accordion-content rule"
    assert "max-height: none" in content.group(0)
    assert "max-height: 300px" not in content.group(0)


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

