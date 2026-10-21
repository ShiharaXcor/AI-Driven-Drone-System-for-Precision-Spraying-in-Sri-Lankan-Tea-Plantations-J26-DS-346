import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from . import config
from .gps_logger import gps_loop
from .routers import decide, controls, events, infer, spray_tests, reports, gps_history

STATIC = Path(__file__).resolve().parents[1] / "static"
(STATIC / "out").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(gps_loop()) if config.GPS_LOG_INTERVAL_S > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Safe Spray API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

for r in (decide, controls, events, infer, spray_tests, reports, gps_history):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"ok": True}