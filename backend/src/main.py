from fastapi import FastAPI

from src.components.router import router as components_router

app = FastAPI(title="TeaDrone API")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(components_router, prefix="/api")