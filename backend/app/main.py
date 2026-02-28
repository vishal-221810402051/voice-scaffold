from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.routes_ast import router as ast_router

app = FastAPI(title="Voice-Scaffold API")

app.include_router(ast_router)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


@app.get("/")
def health_check():
    return {"status": "Voice-Scaffold backend running"}
