"""
Audit Runner - Main orchestrator for SEO audits.

Coordinates page fetching, data collection, and scoring.
"""
import asyncio
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from app.logger import logger
from app.services.page_fetcher import PageFetcher
from app.services.collectors.meta_collector import MetaCollector
from app.services.collectors.schema_collector import SchemaCollector
from app.services.collectors.robots_collector import RobotsCollector
from app.services.collectors.llms_txt_collector import LlmsTxtCollector
from app.services.collectors.sitemap_collector import SitemapCollector
from app.services.collectors.perf_collector import PerfCollector
from app.services.scoring.engine import ScoringEngine
from app.schemas.audit_result import AuditResult


class AuditRunner:
    """Orchestrates the complete audit process."""
    
    def __init__(self):
        self.page_fetcher = PageFetcher()
        self.meta_collector = MetaCollector()
        self.schema_collector = SchemaCollector()
        self.robots_collector = RobotsCollector()
        self.llms_txt_collector = LlmsTxtCollector()
        self.sitemap_collector = SitemapCollector()
        self.perf_collector = PerfCollector()
        self.scoring_engine = ScoringEngine()
    
    async def run(self, url: str, include_perf: bool = True, job_id: str = "") -> AuditResult:
        """
        Run complete audit on a URL.
        
        Args:
            url: The URL to audit
            include_perf: Whether to include PageSpeed metrics
            job_id: The unique ID of the audit job
            
        Returns:
            AuditResult with scores and checks
        """
        started_at = datetime.utcnow()
        
        try:
            # 1. Fetch the page
            logger.info(f"Starting audit for {url} (job_id={job_id})")
            fetch_result = await self.page_fetcher.fetch(url)
            
            if fetch_result.error:
                return self._error_result(url, started_at, fetch_result.error, job_id)
            
            html = fetch_result.html
            final_url = fetch_result.final_url or url
            status_code = fetch_result.status_code
            redirect_count = len(fetch_result.redirect_chain)
            
            # 2. Collect metadata from HTML
            meta_data = self.meta_collector.collect(html, final_url)
            schema_data = self.schema_collector.collect(html)
            
            # 3. Fetch auxiliary data in parallel
            base_url = self._get_base_url(final_url)
            
            robots_task = asyncio.create_task(self.robots_collector.fetch(base_url))
            llms_task = asyncio.create_task(self.llms_txt_collector.fetch(base_url))
            sitemap_task = asyncio.create_task(self.sitemap_collector.fetch(base_url))
            
            if include_perf:
                perf_task = asyncio.create_task(self.perf_collector.fetch(final_url))
            
            robots_data = await robots_task
            llms_data = await llms_task
            sitemap_data = await sitemap_task
            perf_data = await perf_task if include_perf else None
            
            # 4. Check for date signals
            has_published_date = self._has_date(html)
            
            # 5. Prepare data for Scoring Engine
            # Calculate quality for llms.txt
            llms_quality = 0
            if llms_data.exists:
                llms_quality += 5 if llms_data.has_description else 0
                llms_quality += 5 if llms_data.has_contact else 0
            
            # Simple heading order validation (placeholder logic)
            heading_order_valid = True 
            if meta_data.h1_tags and meta_data.h2_tags and meta_data.h3_tags:
                heading_order_valid = True # In a real implementation we'd check raw HTML positions
            
            scores = self.scoring_engine.score(
                # Page data
                status_code=status_code,
                redirect_count=redirect_count,
                is_https=final_url.startswith("https://"),
                html=html,
                main_text=meta_data.text_content,
                word_count=meta_data.word_count,
                
                # Meta
                has_title=bool(meta_data.title),
                title_length=meta_data.title_length,
                has_meta_description=bool(meta_data.description),
                meta_description_length=meta_data.description_length,
                has_canonical=bool(meta_data.canonical),
                canonical_matches_url=meta_data.canonical == final_url if meta_data.canonical else False,
                has_noindex="noindex" in (meta_data.robots_meta or "").lower(),
                has_viewport=bool(meta_data.viewport),
                h1_count=len(meta_data.h1_tags),
                h2_count=len(meta_data.h2_tags),
                heading_order_valid=heading_order_valid,
                
                # NEW: Additional meta
                has_charset=True, # Assuming beautifulsoup parsed it, usually true for correct HTML
                has_html_lang=bool(meta_data.lang),
                total_images=meta_data.images_total,
                images_with_alt=meta_data.images_with_alt,
                internal_link_count=meta_data.internal_links,
                external_link_count=meta_data.external_links,
                
                # External data
                has_sitemap=sitemap_data.exists,
                robots_available=robots_data.exists,
                ai_bots_allowed=robots_data.allowed_bots,
                ai_bots_blocked=robots_data.disallowed_bots,
                llms_txt_exists=llms_data.exists,
                llms_txt_quality=llms_quality,
                has_schema=bool(schema_data.schemas),
                schema_types=[s.get("@type", "Unknown") for s in schema_data.schemas],
                has_og_tags=bool(meta_data.og_tags),
                has_twitter_cards=bool(meta_data.twitter_tags),
                has_faq_schema=any(s.get("@type") == "FAQPage" for s in schema_data.schemas),
                has_published_date=has_published_date,
                has_trust_signals=False, # Placeholder
                has_clear_purpose=True, # Placeholder
                
                # Performance
                perf_available=perf_data is not None,
                performance_score=perf_data.score if perf_data else None
            )
            
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()
            
            return AuditResult(
                job_id=job_id,
                url=url,
                final_url=final_url,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=round(duration, 2),
                scores=scores.scores,
                confidence=scores.confidence,
                caps_applied=scores.caps_applied,
                labels=scores.labels,
                checks=scores.checks,
                scoring_version="1.1"
            )
            
        except Exception as e:
            logger.exception(f"Audit failed: {e}")
            return self._error_result(url, started_at, str(e), job_id)
    
    def _get_base_url(self, url: str) -> str:
        """Extract base URL (scheme + host)."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _has_date(self, html: str) -> bool:
        """Check if page has a published/updated date."""
        # Check JSON-LD
        if '"datePublished"' in html or '"dateModified"' in html:
            return True
        
        # Check meta tags
        lower = html.lower()
        if 'article:published' in lower or 'article:modified' in lower:
            return True
        
        # Check time element
        if '<time' in html:
            return True
        
        return False
    
    def _error_result(self, url: str, started_at: datetime, error: str, job_id: str) -> AuditResult:
        """Create error result."""
        completed_at = datetime.utcnow()
        return AuditResult(
            job_id=job_id,
            url=url,
            final_url=url,
            status="failed",
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=round((completed_at - started_at).total_seconds(), 2),
            # Missing scores/confidence/etc is allowed as Optional in schema
            scores=None, 
            confidence=None,
            caps_applied=[],
            labels=[],
            checks=[],
            scoring_version="1.1",
            error=str(error)
        )

