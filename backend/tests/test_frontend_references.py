import os


def test_frontend_references_sar_ais_association_endpoint():
    """
    Lightweight “frontend test”: ensure the shipped frontend code references the new backend endpoint.
    This avoids introducing a JS test runner while still preventing accidental regressions.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    frontend_main = os.path.join(repo_root, "frontend", "main.js")

    with open(frontend_main, "r", encoding="utf-8") as f:
        content = f.read()

    assert "/api/detections/sar-ais-association" in content

