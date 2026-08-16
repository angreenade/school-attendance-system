import os
import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, SessionLocal, engine
from .routers import attendance, auth, classes, locations, students
from . import models
from .seed_data import run_seed

Base.metadata.create_all(bind=engine)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
# Populated by the Docker build (see Dockerfile): the built Vite frontend.
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend_dist")


def _auto_seed_if_empty():
    """Runs once, only on a truly empty database (fresh deploy / first boot).
    Never wipes existing data -- unlike seed.py, which is a destructive dev
    convenience script. This is what lets a cloud deployment come up with a
    working demo login and sample data with zero manual setup steps."""
    db = SessionLocal()
    try:
        if db.query(models.AdminUser).count() > 0:
            return
        admin_password = settings.admin_password or secrets.token_urlsafe(9)
        teacher_password = settings.teacher_password or secrets.token_urlsafe(9)
        stats = run_seed(db, wipe=False, admin_password=admin_password, teacher_password=teacher_password)
        banner = "\n".join([
            "=" * 64,
            "First boot: seeded demo data.",
            f"  admin login:   admin / {admin_password}",
            f"  teacher login: teacher / {teacher_password}",
            "(Set ATTENDANCE_ADMIN_PASSWORD / ATTENDANCE_TEACHER_PASSWORD env vars",
            " to control these instead of relying on the generated password above.)",
            f"Seeded {stats['students']} students, {stats['class_sections']} class sections, "
            f"{stats['locations']} locations, {stats['attendance_logs']} attendance logs.",
            "=" * 64,
        ])
        print(banner)
    finally:
        db.close()


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your actual kiosk/dashboard origin(s) in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    _auto_seed_if_empty()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(locations.router)
app.include_router(classes.router)
app.include_router(attendance.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# ---------- Serve the built frontend (if present) ----------
# In the single-service Docker image, the Vite build output is copied into
# app/frontend_dist/ at build time. Locally (npm run dev), the frontend runs
# on its own Vite dev server instead and this block is simply inert.
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend-assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        """Anything that isn't an /api, /static, or /assets route falls
        through to the SPA's index.html so client-side routing (react-router)
        can take over -- this is what makes /login, /kiosk, /dashboard/*
        work on a hard refresh or a direct link."""
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
