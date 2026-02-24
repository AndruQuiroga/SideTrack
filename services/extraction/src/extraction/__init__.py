"""Sidetrack audio feature extraction service.

This is a standalone microservice that handles GPU-heavy audio analysis
(librosa, openl3, tensorflow). It communicates with the main Sidetrack API
over HTTP and is deployed separately — typically on GPU-capable hardware.

Run locally:
    cd services/extraction
    uv run uvicorn extraction.app:app --reload --port 8800
"""
