from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    ai_chat,
    analytics,
    assessments,
    auth,
    curriculum,
    generation,
    health,
    intervention_notes,
    me,
    platform,
    questions,
    schools,
)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    app = FastAPI(title=settings.app_name)

    # CORS: in dev the SPA runs on :5173 (Vite) and proxies /api to FastAPI on
    # :8000, so this is mostly same-origin. In deploy (Firebase Hosting + Cloud
    # Run) the browser hits the Cloud Run URL directly, so the deployed origin
    # must be in ALLOWED_ORIGINS. Driven from env so we never have to redeploy
    # the image just to add a domain.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(curriculum.router)
    app.include_router(generation.router)
    app.include_router(questions.router)
    app.include_router(assessments.router)
    app.include_router(assessments.submissions_router)
    app.include_router(analytics.router)
    app.include_router(intervention_notes.router)
    app.include_router(schools.router)
    app.include_router(ai_chat.router)
    app.include_router(ai_chat.admin_router)
    app.include_router(platform.router)
    return app


app = create_app()
