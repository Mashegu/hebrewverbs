from fastapi import FastAPI

app = FastAPI(
    title="HebrewVerbs API",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "HebrewVerbs Backend is running"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
