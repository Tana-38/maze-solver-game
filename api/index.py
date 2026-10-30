"""Vercel serverless entry point: every /api/* request is routed here (see vercel.json).

Vercel's Python runtime looks for a BaseHTTPRequestHandler subclass named
``handler``; it is the same Handler the local server uses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.server import Handler  # noqa: E402


class handler(Handler):  # noqa: N801  (name required by Vercel)
    """Handler for Vercel; identical to the local one."""
