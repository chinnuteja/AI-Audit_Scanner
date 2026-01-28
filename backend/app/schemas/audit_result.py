"""
Pydantic schemas for audit responses.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    """Individual check result."""
    id: str
    name: str
    category: str
    points_awarded: int
    points_possible: int
    status: Literal["pass", "fail", "partial", "skip", "info"]
    evidence: Optional[str] = None
    how_to_fix: Optional[str] = None
    severity: str = "P2"


class Scores(BaseModel):
    """Score breakdown."""
    technical: int = Field(..., ge=0, le=100)
    content: int = Field(..., ge=0, le=100)
    ai: int = Field(..., ge=0, le=100)
    overall: int = Field(..., ge=0, le=100)


class Confidence(BaseModel):
    """Confidence assessment."""
    level: Literal["high", "medium", "low"]
    score: int
    missing: list[str]
    reason: str


class AuditResult(BaseModel):
    """Complete audit response."""
    # Identification
    job_id: str
    
    # Request info
    url: str
    final_url: str
    
    # Status
    status: Literal["pending", "running", "completed", "failed"]
    
    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0
    
    # Scores (only if completed)
    scores: Optional[Scores] = None
    confidence: Optional[Confidence] = None
    
    # Details
    caps_applied: list[str] = []
    labels: list[str] = []
    checks: list[CheckResult] = []
    
    # Error (if failed)
    error: Optional[str] = None
    
    # Metadata
    scoring_version: str = "1.0"
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "final_url": "https://example.com",
                "status": "completed",
                "started_at": "2024-01-01T12:00:00Z",
                "completed_at": "2024-01-01T12:00:05Z",
                "duration_seconds": 5.2,
                "scores": {
                    "technical": 85,
                    "content": 72,
                    "ai": 60,
                    "overall": 72
                },
                "confidence": {
                    "level": "high",
                    "score": 90,
                    "missing": ["performance"],
                    "reason": "Most data sources available"
                }
            }
        }
