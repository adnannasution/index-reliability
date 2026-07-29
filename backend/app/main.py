"""
Entrypoint FastAPI: Reliability & Maintenance Optimization Dashboard
CDU Recovery RDMP Refinery Unit VI Pertamina Balongan (Unit 11).

Aplikasi ini adalah penerjemahan skrip MATLAB CDU_PdM_Balongan.m (v3.0) menjadi
web app interaktif, ditambah diagram RBD interaktif dan optimasi biaya-keandalan
multi-objektif berbasis NSGA-II.

Prinsip (§1):
  * seluruh rumus bersumber dari referensi akademik/standar (lihat /api/meta/references);
  * MATLAB adalah sumber kebenaran untuk metode, parameter default, mapping FS,
    struktur RBD, dan daftar grafik;
  * tidak ada daftar tag/tanggal/jumlah baris yang di-hard-code: semua
    diturunkan dari berkas yang di-upload;
  * tidak ada unhandled exception yang sampai ke pengguna: setiap galat menjadi
    pesan JSON yang informatif.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.data_loader import DataLoadError
from app.routers import (
    analysis,
    export,
    interval,
    meta,
    optimization,
    rbd_router,
    simulation,
    upload,
)

logger = logging.getLogger("cdu")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s | %(message)s"
)

app = FastAPI(
    title="Reliability & Maintenance Optimization Dashboard: CDU RU VI Balongan",
    description=(
        "Analisis keandalan dan optimasi pemeliharaan Crude Distillation Unit "
        "RU VI Balongan. Port dari CDU_PdM_Balongan.m v3.0 dengan tambahan RBD "
        "interaktif dan optimasi biaya-keandalan NSGA-II."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS: Vite dev server berjalan di port 5173. Daftar dapat ditambah lewat
# variabel lingkungan CORS_ORIGINS (dipisah koma) saat penyebaran.
_default_origins = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:4173", "http://127.0.0.1:4173",
    "http://localhost:3000", "http://127.0.0.1:3000",
]
_env_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
# Bila CORS_ORIGINS = "*", izinkan seluruh origin (untuk tunnel publik).
if _env_origins == ["*"]:
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_credentials=False,
        allow_methods=["*"], allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_env_origins or _default_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(upload.router)
app.include_router(analysis.router)
app.include_router(rbd_router.router)
app.include_router(simulation.router)
app.include_router(interval.router)
app.include_router(optimization.router)
app.include_router(meta.router)
app.include_router(export.router)


# ==========================================================================
# Penanganan galat menyeluruh (§1.4): tidak ada stack trace ke pengguna
# ==========================================================================
@app.exception_handler(DataLoadError)
async def handle_data_load_error(_: Request, exc: DataLoadError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "kind": "data",
                 "hint": "Periksa nama kolom dan sheet pada berkas Excel."},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Ubah galat validasi Pydantic menjadi kalimat berbahasa Indonesia."""
    parts = []
    for e in exc.errors():
        loc = " -> ".join(str(x) for x in e.get("loc", []) if x != "body")
        parts.append(f"{loc or 'permintaan'}: {e.get('msg', 'tidak sah')}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Permintaan tidak sah. " + "; ".join(parts[:6]),
            "kind": "validation",
            "hint": "Periksa nilai pada panel pengaturan.",
        },
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail), "kind": "http"},
    )


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    """Jaring terakhir: catat penuh di log server, ringkas untuk pengguna."""
    logger.exception("Galat tak tertangani pada %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Terjadi galat tak terduga di server saat memproses permintaan ini. "
                f"Jenis: {type(exc).__name__}. Periksa log server untuk rincian."
            ),
            "kind": "internal",
            "hint": "Coba unggah ulang berkas atau kembalikan parameter ke nilai default.",
        },
    )


@app.get("/api/health", tags=["sistem"])
async def health() -> Dict[str, Any]:
    """Healthcheck: dipakai docker-compose dan halaman status frontend."""
    import numpy
    import pandas
    import pymoo
    import scipy

    return {
        "status": "ok",
        "app": "cdu-reliability-dashboard",
        "version": app.version,
        "unit": "RU VI Balongan: Unit 11 (CDU)",
        "pustaka": {
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "pandas": pandas.__version__,
            "pymoo": pymoo.__version__,
        },
    }


# ==========================================================================
# Sajian frontend statis (mode produksi & tunnel publik)
# ==========================================================================
# Bila `frontend/dist` sudah dibangun, seluruh permintaan non-/api dilayani
# dari sana. Rute "/" mengembalikan index.html dan setiap rute SPA lain juga
# dipetakan ke index.html supaya routing sisi klien berjalan.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if _DIST.is_dir() and (_DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def _index() -> FileResponse:
        return FileResponse(_DIST / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    async def _spa(path: str) -> FileResponse:
        # File aset lain (favicon, dsb.) dilayani apa adanya, sisanya index SPA.
        p = _DIST / path
        if p.is_file():
            return FileResponse(p)
        return FileResponse(_DIST / "index.html")
else:
    @app.get("/", tags=["sistem"])
    async def root() -> Dict[str, str]:
        return {
            "app": "Reliability & Maintenance Optimization Dashboard: CDU RU VI Balongan",
            "docs": "/api/docs",
            "health": "/api/health",
            "catatan": "Frontend belum dibangun. Jalankan `npm run build` di folder frontend.",
        }
