"""
Audit API endpoints.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional
import uuid

from app.logger import logger
from app.services.audit_runner import AuditRunner

router = APIRouter()

# In-memory audit storage
_audits: Dict[str, Any] = {}


class AuditRequest(BaseModel):
    """Request body for starting an audit."""
    url: HttpUrl
    include_perf: bool = True


class AuditResponse(BaseModel):
    """Response for audit status."""
    job_id: str
    status: str
    url: str


@router.post("", response_model=AuditResponse)
async def start_audit(request: AuditRequest, background_tasks: BackgroundTasks):
    """Start a new SEO audit."""
    job_id = str(uuid.uuid4())
    url = str(request.url)
    
    # Store initial state
    _audits[job_id] = type('AuditState', (), {
        'job_id': job_id,
        'url': url,
        'status': 'pending',
        'result': None,
        'final_url': url
    })()
    
    # Run audit in background
    background_tasks.add_task(_run_audit, job_id, url, request.include_perf)
    
    logger.info(f"Started audit {job_id} for {url}")
    return AuditResponse(job_id=job_id, status="pending", url=url)


async def _run_audit(job_id: str, url: str, include_perf: bool):
    """Background task to run the audit."""
    try:
        _audits[job_id].status = "running"
        
        runner = AuditRunner()
        result = await runner.run(url, include_perf, job_id=job_id)
        
        _audits[job_id].status = "completed"
        _audits[job_id].result = result
        _audits[job_id].final_url = result.final_url
        
        logger.info(f"Completed audit {job_id}")
        
    except Exception as e:
        logger.exception(f"Audit {job_id} failed: {e}")
        _audits[job_id].status = "failed"
        _audits[job_id].error = str(e)


@router.get("/{job_id}")
async def get_audit(job_id: str):
    """Get audit status and results."""
    if job_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    audit = _audits[job_id]
    
    response = {
        "job_id": job_id,
        "status": audit.status,
        "url": audit.url,
        "final_url": audit.final_url
    }
    
    if audit.status == "completed" and audit.result:
        result = audit.result
        response.update({
            "scores": result.scores,
            "confidence": result.confidence,
            "caps_applied": result.caps_applied,
            "labels": result.labels,
            "checks": [c.model_dump() if hasattr(c, 'model_dump') else c.__dict__ for c in result.checks],
            "duration_seconds": result.duration_seconds,
            "scoring_version": result.scoring_version
        })
    
    if audit.status == "failed" and hasattr(audit, 'error'):
        response["error"] = audit.error
    
    return response


@router.get("/{job_id}/pdf")
async def get_audit_pdf(job_id: str):
    """Get audit report as PDF."""
    if job_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    audit = _audits[job_id]
    if audit.status != "completed":
        raise HTTPException(status_code=400, detail="Audit not completed yet")
    
    from app.services.pdf_generator import PdfGenerator
    from fastapi.responses import Response
    
    generator = PdfGenerator()
    pdf_bytes = generator.generate(audit.result, audit.final_url)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=svata_audit_{job_id[:8]}.pdf"
        }
    )
