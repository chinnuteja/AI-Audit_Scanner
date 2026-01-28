"""
Health check endpoint.
"""

from fastapi import APIRouter
from app.services.circuit_breaker import get_circuit_breaker

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "ok"}


@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with circuit breaker status."""
    circuit = get_circuit_breaker()
    
    return {
        "status": "ok",
        "circuit_breaker": circuit.get_status()
    }
