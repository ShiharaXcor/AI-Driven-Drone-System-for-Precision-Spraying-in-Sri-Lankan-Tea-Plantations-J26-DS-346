from fastapi import FastAPI

app = FastAPI(title="TeaDrone API")


@app.get("/health")
def health():
    return {"status": "ok"}