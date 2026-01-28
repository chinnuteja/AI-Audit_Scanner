"""
Pydantic schemas for audit requests.
"""

from pydantic import BaseModel, HttpUrl, Field


class AuditRequest(BaseModel):
    """Request to start an SEO audit."""
    url: str = Field(..., description="URL to audit")
    include_perf: bool = Field(True, description="Include PageSpeed metrics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "include_perf": True
            }
        }


class AuditStatusRequest(BaseModel):
    """Request to check audit status."""
    job_id: str = Field(..., description="Audit job ID")
