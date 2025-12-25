#!/usr/bin/env python3
"""Entry point for the Antigravity Quota API server."""

import os

import uvicorn
from dotenv import load_dotenv

from ag_quota_api import app

# Load environment variables from .env file
load_dotenv()

# Server port (loaded from .env, default 8000)
PORT = int(os.getenv("PORT", "8000"))


def main():
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
