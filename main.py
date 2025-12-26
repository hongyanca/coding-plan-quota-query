#!/usr/bin/env python3
"""Entry point for the Antigravity Quota API server."""

import logging

import uvicorn

# Configure logging before importing app modules
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:     %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from src.api import app
from src.config import PORT


def main():
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()

