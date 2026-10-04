from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, releases, builders
from app.core.exceptions import QuorumException

app = FastAPI(
    title="Quorum Backend API",
    description="FastAPI Backend for Quorum verification engine.",
    version="1.0.0"
)

# CORS configuration for frontend / cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Exception Handlers
@app.exception_handler(QuorumException)
async def quorum_exception_handler(request: Request, exc: QuorumException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

# Include Routers
app.include_router(health.router)
app.include_router(releases.router)
app.include_router(builders.router)


@app.get("/")
async def root():
    return {
        "title": "Quorum Backend API",
        "docs": "/docs",
        "health": "/health",
        "status": "running"
    }
