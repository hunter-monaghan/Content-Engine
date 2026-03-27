from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from content_engine.config import Settings
from content_engine.pipeline.orchestrator import ContentEngine


@dataclass(slots=True)
class JobRecord:
    job_id: str
    niche: str
    limit: int
    ab_hooks: int
    requester_ip: str
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    error: str | None = None
    outputs: list[dict[str, Any]] = field(default_factory=list)


class GenerateRequest(BaseModel):
    niche: str = Field(default="storytime", min_length=2, max_length=40)
    limit: int = Field(default=1, ge=1, le=5)
    ab_hooks: int = Field(default=2, ge=1, le=5)


class JobRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.jobs: dict[str, JobRecord] = {}
        self.ip_history: dict[str, list[float]] = {}
        self.lock = threading.Lock()

    def create(self, request: GenerateRequest, requester_ip: str) -> JobRecord:
        requester_ip = requester_ip or "unknown"
        with self.lock:
            self._enforce_rate_limit(requester_ip)
            job = JobRecord(
                job_id=uuid4().hex,
                niche=request.niche,
                limit=request.limit,
                ab_hooks=request.ab_hooks,
                requester_ip=requester_ip,
            )
            self.jobs[job.job_id] = job
            self.ip_history.setdefault(requester_ip, []).append(time.time())
        return job

    def start(self, job_id: str) -> None:
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()

    def list_jobs(self) -> list[dict[str, Any]]:
        with self.lock:
            return [asdict(job) for job in sorted(self.jobs.values(), key=lambda item: item.created_at, reverse=True)]

    def get(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            return asdict(job)

    def _run_job(self, job_id: str) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.status = "running"

        engine = ContentEngine(self.settings)
        try:
            packages = engine.run_once(niche=job.niche, limit=job.limit, ab_hooks=job.ab_hooks)
            outputs = [_serialize_package(package) for package in packages]
            with self.lock:
                job.status = "completed"
                job.outputs = outputs
                job.finished_at = datetime.now(timezone.utc).isoformat()
        except Exception as exc:  # noqa: BLE001
            with self.lock:
                job.status = "failed"
                job.error = str(exc)
                job.finished_at = datetime.now(timezone.utc).isoformat()

    def _enforce_rate_limit(self, requester_ip: str) -> None:
        now = time.time()
        window_start = now - self.settings.job_window_seconds
        history = [value for value in self.ip_history.get(requester_ip, []) if value >= window_start]
        self.ip_history[requester_ip] = history
        if len(history) >= self.settings.max_jobs_per_ip:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Rate limit reached for this IP. Try again later or use an admin token."
                ),
            )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title=settings.site_name)
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
    registry = JobRegistry(settings)

    app.mount("/media", StaticFiles(directory=str(settings.output_dir)), name="media")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "site_name": settings.site_name,
                "public_generation_enabled": settings.public_generation_enabled,
                "max_jobs_per_ip": settings.max_jobs_per_ip,
                "job_window_minutes": settings.job_window_seconds // 60,
            },
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/videos")
    async def list_videos() -> list[dict[str, Any]]:
        return scan_outputs(settings.output_dir)

    @app.get("/api/jobs")
    async def list_jobs() -> list[dict[str, Any]]:
        return registry.list_jobs()

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str) -> dict[str, Any]:
        try:
            return registry.get(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found.") from exc

    @app.post("/api/generate")
    async def generate(request: Request, payload: GenerateRequest) -> JSONResponse:
        _authorize_generation(request, settings)
        job = registry.create(payload, requester_ip=request.client.host if request.client else "unknown")
        registry.start(job.job_id)
        return JSONResponse(asdict(job), status_code=202)

    return app


def scan_outputs(output_dir: Path) -> list[dict[str, Any]]:
    if not output_dir.exists():
        return []
    packages: list[dict[str, Any]] = []
    for metadata_path in sorted(output_dir.glob("*/metadata.json"), reverse=True):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        output_folder = metadata_path.parent.name
        video_path = metadata_path.parent / "final.mp4"
        script_path = metadata_path.parent / "script.txt"
        caption_path = metadata_path.parent / "caption.txt"
        packages.append(
            {
                "variant_id": metadata.get("variant_id", output_folder),
                "title": metadata.get("captions", {}).get("title") or metadata.get("title", output_folder),
                "caption": metadata.get("captions", {}).get("caption") or metadata.get("caption", ""),
                "source": metadata.get("idea", {}).get("source") or metadata.get("source", ""),
                "video_url": f"/media/{output_folder}/final.mp4" if video_path.exists() else None,
                "script_url": f"/media/{output_folder}/script.txt" if script_path.exists() else None,
                "caption_url": f"/media/{output_folder}/caption.txt" if caption_path.exists() else None,
                "metadata_url": f"/media/{output_folder}/metadata.json",
                "created_at": metadata.get("idea", {}).get("created_at", ""),
            }
        )
    return packages


def _serialize_package(package: Any) -> dict[str, Any]:
    output_folder = package.output_dir.name
    return {
        "variant_id": package.variant_id,
        "title": package.captions.title,
        "caption": package.captions.caption,
        "source": package.idea.source,
        "video_url": f"/media/{output_folder}/final.mp4",
        "script_url": f"/media/{output_folder}/script.txt",
        "caption_url": f"/media/{output_folder}/caption.txt",
        "metadata_url": f"/media/{output_folder}/metadata.json",
    }


def _authorize_generation(request: Request, settings: Settings) -> None:
    token = request.headers.get("x-app-token")
    if settings.app_admin_token and token == settings.app_admin_token:
        return
    if settings.public_generation_enabled:
        return
    raise HTTPException(status_code=403, detail="Generation is currently restricted.")
