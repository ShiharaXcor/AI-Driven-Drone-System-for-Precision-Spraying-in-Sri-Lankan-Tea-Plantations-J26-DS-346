from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routers import decide, controls, events, infer, spray_tests

STATIC = Path(__file__).resolve().parents[1] / "static"
(STATIC / "out").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Safe Spray API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

app.include_router(decide.router)
app.include_router(controls.router)
app.include_router(events.router)
app.include_router(infer.router)
app.include_router(spray_tests.router)


@app.get("/api/health")
def health():
    return {"ok": True}