#!/usr/bin/env python

from __future__ import annotations

import uvicorn

from backend.app.core.config import settings


def main() -> None:
    uvicorn.run(
        "backend.app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_use_reloader,
    )


if __name__ == "__main__":
    main()
