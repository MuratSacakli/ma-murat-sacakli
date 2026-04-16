from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from database import init_db
from routers import salons, hairdressers, services, appointments, calls, customers


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="KI-gestützter Telefonassistent für Friseursalons",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(salons.router)
app.include_router(hairdressers.router)
app.include_router(services.router)
app.include_router(appointments.router)
app.include_router(calls.router)
app.include_router(customers.router)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def root():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"Willkommen beim {settings.APP_NAME}", "version": settings.VERSION}


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME}
