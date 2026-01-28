"""
Hard Caps - Prevent inflated scores for broken pages.

Rules:
- 4xx/5xx status → Technical max 20, Overall max 30
- noindex detected → Technical max 40, Overall max 50
- AI bots blocked → AI max 30, labeled "restricted"
"""

from dataclasses import dataclass, field
from typing import Optional

from app.logger import logger


@dataclass
class CapResult:
    """Result of applying caps."""
    technical: int
    content: int
    ai: int
    overall: int
    caps_applied: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)


class CapsEngine:
    """Apply hard caps to prevent inflated scores."""
    
    def apply(
        self,
        technical: int,
        content: int,
        ai: int,
        overall: int,
        status_code: Optional[int],
        has_noindex: bool,
        ai_bots_blocked: bool
    ) -> CapResult:
        """Apply all relevant caps.
        
        Args:
            technical: Raw technical score
            content: Raw content score
            ai: Raw AI score
            overall: Raw overall score
            status_code: HTTP status code (or None)
            has_noindex: Whether page has noindex
            ai_bots_blocked: Whether major AI bots are blocked
            
        Returns:
            CapResult with potentially reduced scores
        """
        result = CapResult(
            technical=technical,
            content=content,
            ai=ai,
            overall=overall
        )
        
        # Cap 1: 4xx/5xx status
        if status_code and status_code >= 400:
            if result.technical > 20:
                result.technical = 20
                result.caps_applied.append(f"technical_capped_20_status_{status_code}")
            if result.overall > 30:
                result.overall = 30
                result.caps_applied.append(f"overall_capped_30_status_{status_code}")
            result.labels.append("error_page")
            logger.info(f"Applied cap: status {status_code} → tech≤20, overall≤30")
        
        # Cap 2: noindex
        if has_noindex:
            if result.technical > 40:
                result.technical = 40
                result.caps_applied.append("technical_capped_40_noindex")
            if result.overall > 50:
                result.overall = 50
                result.caps_applied.append("overall_capped_50_noindex")
            result.labels.append("noindex")
            logger.info("Applied cap: noindex → tech≤40, overall≤50")
        
        # Cap 3: AI bots blocked
        if ai_bots_blocked:
            if result.ai > 30:
                result.ai = 30
                result.caps_applied.append("ai_capped_30_bots_blocked")
            result.labels.append("ai_restricted")
            logger.info("Applied cap: AI bots blocked → ai≤30")
        
        return result
