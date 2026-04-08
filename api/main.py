"""FastAPI приложение — REST API для Mini App и веб-админки."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import api_settings
from api.routers import auth, requests, analytics, departments, users, flow, topics

app = FastAPI(
    title="RequestBot API",
    description="API для управления заявками",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=api_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(requests.router)
app.include_router(analytics.router)
app.include_router(departments.router)
app.include_router(users.router)
app.include_router(flow.router)
app.include_router(topics.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
