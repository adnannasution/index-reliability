"""
Lapisan persistensi PostgreSQL (opsional).

Bila DATABASE_URL tidak diset, semua fungsi menjadi no-op:
aplikasi tetap berjalan dengan penyimpanan in-memory saja
(cocok untuk development lokal tanpa database).

Skema:
    uploaded_files — menyimpan raw bytes berkas Excel beserta metadata,
    sehingga dataset dapat dimuat ulang otomatis setelah redeploy.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator, List

logger = logging.getLogger(__name__)

_pool = None  # psycopg2.pool.ThreadedConnectionPool | None


def init() -> None:
    """Inisialisasi pool koneksi dan jalankan migrasi skema (CREATE TABLE IF NOT EXISTS).

    Dipanggil sekali saat startup aplikasi. Aman diulang (idempotent).
    Bila DATABASE_URL tidak ada atau koneksi gagal, aplikasi tetap jalan
    dengan in-memory store.
    """
    global _pool
    url = os.getenv("DATABASE_URL", "")
    if not url:
        logger.info("DATABASE_URL tidak diset — penyimpanan in-memory saja.")
        return
    try:
        import psycopg2
        import psycopg2.pool

        # psycopg2 menerima postgres:// maupun postgresql://
        if url.startswith("postgresql://"):
            url = "postgres://" + url[len("postgresql://"):]

        _pool = psycopg2.pool.ThreadedConnectionPool(1, 4, url)
        _migrate()
        logger.info("PostgreSQL: terhubung, skema siap.")
    except Exception:
        logger.exception("Gagal terhubung ke PostgreSQL — fallback in-memory.")
        _pool = None


@contextmanager
def _conn() -> Generator:
    """Pinjam koneksi dari pool, kembalikan setelah selesai."""
    assert _pool is not None, "Pool belum diinisialisasi"
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)


def available() -> bool:
    """True bila koneksi PostgreSQL aktif."""
    return _pool is not None


def _migrate() -> None:
    """Buat tabel bila belum ada. Idempotent — aman dijalankan tiap startup."""
    ddl = """
    CREATE TABLE IF NOT EXISTS uploaded_files (
        dataset_id   VARCHAR(12)   PRIMARY KEY,
        kind         VARCHAR(20)   NOT NULL,
        filename     VARCHAR(500)  NOT NULL,
        sheet_name   VARCHAR(500)  NOT NULL,
        uploaded_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
        raw_bytes    BYTEA         NOT NULL
    );
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


def save_file(
    dataset_id: str,
    kind: str,
    filename: str,
    sheet_name: str,
    uploaded_at: str,
    raw_bytes: bytes,
) -> None:
    """Simpan atau perbarui berkas Excel di DB (upsert)."""
    if not available():
        return
    import psycopg2

    sql = """
    INSERT INTO uploaded_files
        (dataset_id, kind, filename, sheet_name, uploaded_at, raw_bytes)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (dataset_id) DO UPDATE
        SET filename    = EXCLUDED.filename,
            sheet_name  = EXCLUDED.sheet_name,
            uploaded_at = EXCLUDED.uploaded_at,
            raw_bytes   = EXCLUDED.raw_bytes;
    """
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    dataset_id, kind, filename, sheet_name, uploaded_at,
                    psycopg2.Binary(raw_bytes),
                ))
            conn.commit()
    except Exception:
        logger.exception("Gagal menyimpan dataset %s ke DB.", dataset_id)


def delete_file(dataset_id: str) -> None:
    """Hapus berkas dari DB."""
    if not available():
        return
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM uploaded_files WHERE dataset_id = %s",
                    (dataset_id,),
                )
            conn.commit()
    except Exception:
        logger.exception("Gagal menghapus dataset %s dari DB.", dataset_id)


def load_all() -> List[dict]:
    """Kembalikan semua berkas tersimpan (terurut dari yang terlama)."""
    if not available():
        return []
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT dataset_id, kind, filename, sheet_name,"
                    "       uploaded_at::text, raw_bytes"
                    " FROM uploaded_files"
                    " ORDER BY uploaded_at"
                )
                rows = cur.fetchall()
        return [
            {
                "dataset_id": r[0],
                "kind":       r[1],
                "filename":   r[2],
                "sheet_name": r[3],
                "uploaded_at": r[4],
                "raw_bytes":  bytes(r[5]),
            }
            for r in rows
        ]
    except Exception:
        logger.exception("Gagal membaca daftar dataset dari DB.")
        return []
