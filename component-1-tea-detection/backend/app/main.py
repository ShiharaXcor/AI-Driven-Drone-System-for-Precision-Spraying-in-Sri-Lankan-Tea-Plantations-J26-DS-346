import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from . import config
from .camera import camera
from .gps_logger import gps_loop
from .settings_store import load_settings
from .routers import (decide, controls, events, infer, spray_tests, reports, gps_history,
                      settings, live, auth)
from .routers import camera as camera_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")

STATIC = Path(__file__).resolve().parents[1] / "static"
(STATIC / "out").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app):
    load_settings()
    if config.ADMIN_PASSWORD == "change-me-now" or config.SECRET_KEY == "dev-secret-change-me":
        log.warning("Default ADMIN_PASSWORD or SECRET_KEY in use. Set your own values in .env")
    task = asyncio.create_task(gps_loop()) if config.GPS_LOG_INTERVAL_S > 0 else None
    yield
    if task:
        task.cancel()
    camera.stop()


app = FastAPI(title="Safe Spray API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"] if "*" in config.CORS_ORIGINS else config.CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


for r in (decide, controls, events, infer, spray_tests, reports, gps_history,
          settings, camera_router, live, auth):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"ok": True}