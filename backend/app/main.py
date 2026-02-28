from fastapi import FastAPI

app = FastAPI(title="Voice-Scaffold API")

@app.get("/")
def health_check():
    return {"status": "Voice-Scaffold backend running"}
