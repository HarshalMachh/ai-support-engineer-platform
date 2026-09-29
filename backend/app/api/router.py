from fastapi import APIRouter

from app.api.routes import ai, analytics, auth, health, knowledge, tickets, users, ws

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tickets.router)
api_router.include_router(ai.router)
api_router.include_router(knowledge.router)
api_router.include_router(analytics.router)
api_router.include_router(ws.router)
