from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.core.config import BASE_DIR, settings
from backend.app.schemas.position import RebuildRequest


def run_rebuild(request: RebuildRequest) -> dict[str, str]:
    existing_files = {
        file_path.resolve()
        for file_path in settings.data_dir.glob(f"{request.exchange}_*.csv")
    }

    command = [
        sys.executable,
        str(BASE_DIR / "getPosition.py"),
        "--exchange",
        request.exchange,
        "--start-date",
        request.start_date,
        "--end-date",
        request.end_date,
        "--threads",
        str(request.threads),
        "--max-retries",
        str(request.max_retries),
    ]
    completed = subprocess.run(
        command,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        raise RuntimeError(stderr or stdout or "仓位重建失败")

    latest_file = _find_generated_file(request.exchange, existing_files)
    if latest_file is None:
        raise RuntimeError("仓位重建任务完成，但未找到输出 CSV")

    return {
        "file_path": str(latest_file),
        "exchange": request.exchange,
        "start_date": request.start_date,
        "end_date": request.end_date,
    }


def _find_generated_file(exchange: str, existing_files: set[Path]) -> Path | None:
    candidates = sorted(
        settings.data_dir.glob(f"{exchange}_*.csv"),
        key=lambda file_path: file_path.stat().st_mtime,
        reverse=True,
    )
    for file_path in candidates:
        resolved = file_path.resolve()
        if resolved not in existing_files:
            return file_path
    return candidates[0] if candidates else None
