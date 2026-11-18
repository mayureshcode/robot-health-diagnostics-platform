"""Standard-library package assets contract for colcon test."""

from pathlib import Path


def test_dashboard_static_assets_exist() -> None:
    """Ensure the local UI is packaged without a CDN dependency."""
    static = Path(__file__).resolve().parents[1] / "rhm_dashboard" / "static"
    for asset in ("index.html", "app.css", "app.js"):
        path = static / asset
        assert path.is_file() and path.stat().st_size > 100


def test_dashboard_python_module_can_start() -> None:
    """The one-command launcher uses 'python -m rhm_dashboard.server'."""
    server = Path(__file__).resolve().parents[1] / "rhm_dashboard" / "server.py"
    text = server.read_text()
    assert 'if __name__ == "__main__":' in text
    assert "    main()" in text
