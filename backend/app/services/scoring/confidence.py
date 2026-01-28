"""
Confidence Scorer - Compute confidence level based on data coverage.

Levels:
- High: All major data sources available
- Medium: Missing 1-2 sources
- Low: Only partial fetch or major data missing
"""

from dataclasses import dataclass
from typing import Literal


ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass
class ConfidenceResult:
    """Confidence scoring result."""
    level: ConfidenceLevel
    score: int  # 0-100
    missing: list[str]
    reason: str


class ConfidenceScorer:
    """Calculate confidence based on data availability."""
    
    # Required data sources and their weights
    DATA_SOURCES = {
        "html": 25,           # Page HTML fetched
        "robots": 15,         # robots.txt available
        "llms_txt": 10,       # llms.txt checked
        "schema": 15,         # JSON-LD parsed
        "performance": 20,    # PageSpeed metrics
        "sitemap": 5,         # Sitemap found
        "meta": 10,           # Meta tags extracted
    }
    
    def score(
        self,
        html_available: bool,
        robots_available: bool,
        llms_txt_checked: bool,
        schema_extracted: bool,
        perf_available: bool,
        sitemap_available: bool,
        meta_extracted: bool
    ) -> ConfidenceResult:
        """Calculate confidence score.
        
        Args:
            html_available: Was HTML successfully fetched?
            robots_available: Was robots.txt fetched?
            llms_txt_checked: Was llms.txt checked?
            schema_extracted: Were schemas extracted?
            perf_available: Are performance metrics available?
            sitemap_available: Was sitemap found?
            meta_extracted: Were meta tags extracted?
            
        Returns:
            ConfidenceResult with level, score, and missing items
        """
        available = {
            "html": html_available,
            "robots": robots_available,
            "llms_txt": llms_txt_checked,
            "schema": schema_extracted,
            "performance": perf_available,
            "sitemap": sitemap_available,
            "meta": meta_extracted,
        }
        
        # Calculate score
        total_score = 0
        missing = []
        
        for source, weight in self.DATA_SOURCES.items():
            if available.get(source, False):
                total_score += weight
            else:
                missing.append(source)
        
        # Determine level
        if total_score >= 80:
            level = "high"
            reason = "All major data sources available"
        elif total_score >= 50:
            level = "medium"
            reason = f"Missing: {', '.join(missing[:3])}"
        else:
            level = "low"
            reason = f"Significant data missing: {', '.join(missing[:3])}"
        
        return ConfidenceResult(
            level=level,
            score=total_score,
            missing=missing,
            reason=reason
        )
