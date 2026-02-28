from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes_ast import router as ast_router
from app.api.routes_generate import router as gen_router
from app.api.routes_run import router as run_router

app = FastAPI(title="Voice-Scaffold API")

app.include_router(ast_router)
app.include_router(gen_router)
app.include_router(run_router)

@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request, exc):
    # Normalize to 400 for deterministic demo behavior
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.get("/")
def health_check():
    return {"status": "Voice-Scaffold backend running"}
