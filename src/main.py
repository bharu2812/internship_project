from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_400_BAD_REQUEST
from routes.hod import router as hod_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hod_router)

# Custom handler for missing fields
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    missing_fields = [
        err["loc"][-1]
        for err in errors
        if err["type"] == "missing"
    ]
    if missing_fields:
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content={"error": f"You didn't pass the required attribute: {', '.join(missing_fields)}"}
        )
    # fallback to default error if not missing field
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"detail": errors})
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Student Application Portal for University Internship Selection",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)