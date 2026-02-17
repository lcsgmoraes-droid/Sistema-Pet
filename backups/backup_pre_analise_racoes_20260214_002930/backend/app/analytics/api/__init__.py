"""
Analytics API - REST Endpoints
===============================

API REST read-only para analytics.

Exporta o router principal para registro no FastAPI app.
"""

from app.analytics.api.routes import router

__all__ = ['router']
