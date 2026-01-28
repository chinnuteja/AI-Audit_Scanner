"""
Performance Collector - Fetch PageSpeed Insights data.
"""
import httpx
from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.logger import logger


@dataclass
class PerfData:
    """PageSpeed performance data."""
    score: int = 0
    lcp: float = 0.0
    fid: float = 0.0
    cls: float = 0.0
    fcp: float = 0.0
    ttfb: float = 0.0
    speed_index: float = 0.0
    error: Optional[str] = None


class PerfCollector:
    """Fetches PageSpeed Insights data."""
    
    PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    async def fetch(self, url: str) -> Optional[PerfData]:
        """Fetch PageSpeed data for URL."""
        if not settings.PAGESPEED_ENABLED:
            return None
            
        try:
            params = {
                "url": url,
                "strategy": "mobile",
                "category": "performance"
            }
            
            if settings.PAGESPEED_API_KEY:
                params["key"] = settings.PAGESPEED_API_KEY
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(self.PAGESPEED_API, params=params)
                
                if response.status_code != 200:
                    logger.warning(f"PageSpeed API error: {response.status_code}")
                    return PerfData(error=f"API error: {response.status_code}")
                
                data = response.json()
                return self._parse(data)
                
        except Exception as e:
            logger.warning(f"PageSpeed fetch failed: {e}")
            return PerfData(error=str(e))
    
    def _parse(self, data: dict) -> PerfData:
        """Parse PageSpeed API response."""
        perf = PerfData()
        
        try:
            lh = data.get("lighthouseResult", {})
            categories = lh.get("categories", {})
            audits = lh.get("audits", {})
            
            # Overall score
            perf_cat = categories.get("performance", {})
            perf.score = int((perf_cat.get("score", 0) or 0) * 100)
            
            # Core Web Vitals
            if "largest-contentful-paint" in audits:
                perf.lcp = audits["largest-contentful-paint"].get("numericValue", 0) / 1000
            
            if "max-potential-fid" in audits:
                perf.fid = audits["max-potential-fid"].get("numericValue", 0)
            
            if "cumulative-layout-shift" in audits:
                perf.cls = audits["cumulative-layout-shift"].get("numericValue", 0)
            
            if "first-contentful-paint" in audits:
                perf.fcp = audits["first-contentful-paint"].get("numericValue", 0) / 1000
            
            if "server-response-time" in audits:
                perf.ttfb = audits["server-response-time"].get("numericValue", 0)
            
            if "speed-index" in audits:
                perf.speed_index = audits["speed-index"].get("numericValue", 0) / 1000
                
        except Exception as e:
            logger.error(f"PageSpeed parse error: {e}")
            perf.error = str(e)
        
        return perf
