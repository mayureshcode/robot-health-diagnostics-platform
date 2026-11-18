"""Local-first, read-only FastAPI health dashboard with token-protected WebSocket."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from functools import lru_cache
import hmac
import os
from threading import RLock
from time import monotonic
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import ValidationError

from rhm_dashboard.schema import HealthStore, Snapshot, WebSocketAuth, WebSocketMessage


STATIC = Path(__file__).resolve().parent / "static"


def _env(name: str, default: str = "") -> str:
    """Read a runtime configuration variable without embedding secrets."""
    return os.environ.get(name, default)


def _is_local(client: str | None) -> bool:
    """Recognize loopback peers for tokenless localhost development."""
    return client in {"127.0.0.1", "::1", "localhost"}


def create_app(store: HealthStore | None = None) -> FastAPI:
    """Create a self-contained API; tests can inject a store without ROS."""
    dashboard_store = store or HealthStore()
    token = _env("RHM_DASHBOARD_TOKEN")
    host = _env("RHM_DASHBOARD_HOST", "127.0.0.1")
    if not token and host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("RHM_DASHBOARD_TOKEN required when binding a non-loopback interface")

    _rate_lock = RLock()
    _request_times: dict[str, deque[float]] = defaultdict(deque)

    def allowed(client: str | None) -> bool:
        """Bound reads and WebSocket handshakes per client to 90/minute."""
        key = client or "unknown"
        now = monotonic()
        with _rate_lock:
            samples = _request_times[key]
            while samples and now - samples[0] > 60.0:
                samples.popleft()
            if len(samples) >= 90:
                return False
            samples.append(now)
            return True

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        feed = None
        if _env("RHM_DASHBOARD_DISABLE_ROS") != "1":
            from rhm_dashboard.ros_feed import RosFeed
            feed = RosFeed(dashboard_store)
            feed.start()
        try:
            yield
        finally:
            if feed is not None:
                feed.stop()

    app = FastAPI(title="RHM Surveillance Console", version="0.1.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    origins = [origin.strip() for origin in _env("RHM_DASHBOARD_ORIGINS").split(",") if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"],
                       allow_headers=["Authorization"], allow_credentials=False)

    def check_request(request: Request) -> None:
        """Require bearer token or loopback client; throttle reads per peer."""
        if not allowed(request.client.host if request.client else None):
            raise HTTPException(status_code=429, detail="Too many requests")
        if token:
            auth = request.headers.get("authorization", "")
            if not hmac.compare_digest(auth, f"Bearer {token}"):
                raise HTTPException(status_code=401, detail="Authentication required")
        elif not _is_local(request.client.host if request.client else None):
            raise HTTPException(status_code=403, detail="Loopback only")

    @app.get("/", include_in_schema=False)
    async def home(request: Request) -> FileResponse:
        """Serve locally bundled dashboard, without third-party CDNs."""
        if not token and not _is_local(request.client.host if request.client else None):
            raise HTTPException(status_code=403, detail="Loopback only")
        return FileResponse(STATIC / "index.html")

    @app.get("/app.css", include_in_schema=False)
    async def css(request: Request) -> FileResponse:
        """Serve dashboard CSS from package assets."""
        check_request(request) if not token else None
        return FileResponse(STATIC / "app.css")

    @app.get("/app.js", include_in_schema=False)
    async def js(request: Request) -> FileResponse:
        """Serve dashboard client logic from package assets."""
        check_request(request) if not token else None
        return FileResponse(STATIC / "app.js")

    @app.get("/api/snapshot", response_model=Snapshot)
    async def snapshot(request: Request) -> Snapshot:
        """Return only observed data; empty/unknown before ROS connects."""
        check_request(request)
        return dashboard_store.snapshot()

    @app.get("/api/healthz")
    async def healthz() -> dict[str, str]:
        """Report API process readiness only, not robot health."""
        return {"api": "ready", "robot_health": "not_checked"}

    @app.websocket("/ws/health")
    async def websocket_health(ws: WebSocket) -> None:
        """Send versioned state snapshots at a bounded 1 Hz per client."""
        origin = ws.headers.get("origin")
        if not allowed(ws.client.host if ws.client else None):
            await ws.close(code=1008)
            return
        # Browsers send Origin; reject unconfigured cross-origin WebSockets.
        expected = {
            f"http://{host}:{_env('RHM_DASHBOARD_PORT', '8765')}",
            f"http://localhost:{_env('RHM_DASHBOARD_PORT', '8765')}",
            f"http://127.0.0.1:{_env('RHM_DASHBOARD_PORT', '8765')}",
            *origins,
        }
        if origin and origin not in expected:
            await ws.close(code=1008)
            return
        if not token and not _is_local(ws.client.host if ws.client else None):
            await ws.close(code=1008)
            return
        await ws.accept()
        if token:
            try:
                payload = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
                auth = WebSocketAuth.model_validate(payload)
                if not hmac.compare_digest(auth.token, token):
                    await ws.close(code=1008)
                    return
            except (asyncio.TimeoutError, ValidationError, ValueError, WebSocketDisconnect):
                await ws.close(code=1008)
                return
        try:
            while True:
                message = WebSocketMessage(type="snapshot", data=dashboard_store.snapshot())
                await ws.send_json(message.model_dump(mode="json"))
                await asyncio.sleep(1.0)
        except (WebSocketDisconnect, OSError, RuntimeError):
            return

    return app


@lru_cache(maxsize=1)
def get_app() -> FastAPI:
    """Cache the ASGI app for uvicorn's import-string startup."""
    return create_app()


app = get_app()


def main() -> None:
    """Run native Ubuntu dashboard using its environment-configured bind address."""
    import uvicorn

    host = _env("RHM_DASHBOARD_HOST", "127.0.0.1")
    port = int(_env("RHM_DASHBOARD_PORT", "8765"))
    if not 1024 <= port <= 65535:
        raise ValueError("RHM_DASHBOARD_PORT must be 1024..65535")
    uvicorn.run(app, host=host, port=port, log_level="info", workers=1)

if __name__ == "__main__":
    main()
