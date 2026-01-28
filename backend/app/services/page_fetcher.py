"""
Page Fetcher - Core orchestration for fetching pages with HTTP → Firecrawl fallback.

Architecture:
1. URL normalization
2. SSRF protection check
3. Cache lookup
4. HTTP fetch with retries
5. Firecrawl fallback on failure/blocked
6. Store in cache
"""

import hashlib
import asyncio
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.logger import logger
from app.services.firecrawl_adapter import FirecrawlAdapter
from app.services.ssrf_protection import SSRFProtection
from app.services.circuit_breaker import get_circuit_breaker


@dataclass
class PageData:
    """Fetched page data container."""
    url: str
    final_url: str
    normalized_url: str
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    html: str = ""
    fetch_method: str = "unknown"  # 'http' | 'firecrawl'
    fetch_reason: str = "unknown"
    redirect_chain: list[str] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 400


class PageFetcher:
    """Main engine for fetching pages with HTTP → Firecrawl fallback."""
    
    # Class-level lock dictionary for cache stampede prevention
    _fetch_locks: dict[str, asyncio.Lock] = {}
    _locks_lock = asyncio.Lock()
    
    def __init__(self):
        self.http_timeout = settings.HTTP_TIMEOUT
        self.max_redirects = settings.HTTP_MAX_REDIRECTS
        self.max_retries = settings.HTTP_MAX_RETRIES
        self.firecrawl = FirecrawlAdapter()
    
    async def _get_fetch_lock(self, url_hash: str) -> asyncio.Lock:
        """Get or create a lock for a specific URL hash."""
        async with self._locks_lock:
            if url_hash not in self._fetch_locks:
                self._fetch_locks[url_hash] = asyncio.Lock()
            return self._fetch_locks[url_hash]
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL with strict canonicalization.
        
        Handles:
        - Scheme fixing (add https if missing)
        - utm/tracking params removal
        - www subdomain stripping
        - Domain lowercasing
        - Fragment removal
        - Trailing slash removal
        """
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        
        # Normalize domain
        domain = parsed.netloc.lower()
        
        # Strip www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Remove utm params and other tracking params
        if parsed.query:
            params = parse_qs(parsed.query)
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'msclkid', 'ref', 'source', 'mc_cid', 'mc_eid',
                '_ga', '_gl', 'gad_source', 'gbraid', 'wbraid'
            }
            clean_params = {k: v for k, v in params.items() if k not in tracking_params}
            query = urlencode(clean_params, doseq=True) if clean_params else ''
        else:
            query = ''
        
        # Normalize path
        path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
        
        # Build normalized URL
        normalized = urlunparse((
            parsed.scheme.lower(),
            domain,
            path,
            parsed.params,
            query,
            ''  # Remove fragment
        ))
        
        return normalized
    
    async def fetch(self, url: str, force_firecrawl: bool = False) -> PageData:
        """Fetch page with HTTP → Firecrawl fallback.
        
        Args:
            url: URL to fetch
            force_firecrawl: Skip HTTP, go straight to Firecrawl
            
        Returns:
            PageData with HTML content and metadata
        """
        normalized_url = self.normalize_url(url)
        url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()
        
        # SSRF protection
        is_safe, ssrf_reason = SSRFProtection.validate_url(normalized_url)
        if not is_safe:
            logger.warning(f"SSRF protection blocked {normalized_url}: {ssrf_reason}")
            return PageData(
                url=url,
                final_url=normalized_url,
                normalized_url=normalized_url,
                error=f"URL blocked by SSRF protection: {ssrf_reason}"
            )
        
        # Get lock for this URL (prevents stampede)
        fetch_lock = await self._get_fetch_lock(url_hash)
        
        async with fetch_lock:
            logger.info(f"Fetching {normalized_url} (force_firecrawl={force_firecrawl})")
            
            # Try HTTP first (unless force_firecrawl)
            if not force_firecrawl:
                page_data = await self._fetch_http(url, normalized_url)
                
                # If HTTP succeeded, return it
                if page_data.is_success and len(page_data.html) > 500:
                    return page_data
                
                logger.info(f"HTTP fetch insufficient, falling back to Firecrawl")
            
            # Firecrawl fallback
            return await self._fetch_firecrawl(url, normalized_url)
    
    async def _fetch_http(self, original_url: str, normalized_url: str) -> PageData:
        """Fetch page using direct HTTP with retries."""
        redirect_chain = []
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    max_redirects=self.max_redirects,
                    timeout=self.http_timeout
                ) as client:
                    response = await client.get(
                        normalized_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (compatible; AISEOAuditor/1.0)",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                            "Accept-Encoding": "gzip, deflate, br"
                        }
                    )
                    
                    # Track redirect chain
                    for resp in response.history:
                        redirect_chain.append(str(resp.url))
                    
                    final_url = str(response.url)
                    
                    # Handle rate limiting (429)
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 5))
                        if attempt < self.max_retries:
                            logger.warning(f"Rate limited, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            return PageData(
                                url=original_url, final_url=final_url,
                                normalized_url=normalized_url,
                                status_code=429,
                                fetch_method="http", fetch_reason="http_rate_limited",
                                redirect_chain=redirect_chain,
                                error="Rate limited (429)"
                            )
                    
                    # Success
                    if response.status_code == 200:
                        html = response.text
                        
                        # Detect blocked content
                        text_lower = html.lower()
                        if any(x in text_lower for x in ['captcha', 'recaptcha', 'cloudflare']) and len(html) < 5000:
                            return PageData(
                                url=original_url, final_url=final_url,
                                normalized_url=normalized_url,
                                status_code=200, content_type=response.headers.get("content-type"),
                                html=html,
                                fetch_method="http", fetch_reason="blocked_captcha",
                                redirect_chain=redirect_chain
                            )
                        
                        return PageData(
                            url=original_url, final_url=final_url,
                            normalized_url=normalized_url,
                            status_code=200,
                            content_type=response.headers.get("content-type"),
                            html=html,
                            fetch_method="http", fetch_reason="http_ok",
                            redirect_chain=redirect_chain
                        )
                    
                    # 4xx/5xx errors
                    return PageData(
                        url=original_url, final_url=final_url,
                        normalized_url=normalized_url,
                        status_code=response.status_code,
                        fetch_method="http", fetch_reason=f"http_status_{response.status_code}",
                        redirect_chain=redirect_chain,
                        error=f"HTTP {response.status_code}"
                    )
                    
            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    logger.warning(f"HTTP timeout, retrying (attempt {attempt + 1})")
                    await asyncio.sleep(2 ** attempt)
                    continue
                return PageData(
                    url=original_url, final_url=normalized_url,
                    normalized_url=normalized_url,
                    fetch_method="http", fetch_reason="http_timeout",
                    error="HTTP timeout"
                )
            except Exception as e:
                logger.warning(f"HTTP error: {e}")
                return PageData(
                    url=original_url, final_url=normalized_url,
                    normalized_url=normalized_url,
                    fetch_method="http", fetch_reason="http_error",
                    error=str(e)
                )
        
        return PageData(
            url=original_url, final_url=normalized_url,
            normalized_url=normalized_url,
            fetch_method="http", fetch_reason="http_failed",
            error="HTTP fetch failed after retries"
        )
    
    async def _fetch_firecrawl(self, original_url: str, normalized_url: str) -> PageData:
        """Fetch page using Firecrawl (headless browser)."""
        
        # Check circuit breaker
        circuit_breaker = get_circuit_breaker()
        can_call, circuit_reason = circuit_breaker.can_call()
        
        if not can_call:
            logger.warning(f"Circuit breaker: {circuit_reason}")
            return PageData(
                url=original_url, final_url=normalized_url,
                normalized_url=normalized_url,
                fetch_method="firecrawl", fetch_reason=f"firecrawl_{circuit_reason}",
                error=f"Firecrawl unavailable ({circuit_reason})"
            )
        
        try:
            result = await self.firecrawl.scrape(normalized_url)
            
            # Record success
            circuit_breaker.record_success()
            
            return PageData(
                url=original_url,
                final_url=result.get("final_url", normalized_url),
                normalized_url=normalized_url,
                status_code=result.get("status_code"),
                content_type=result.get("content_type"),
                html=result.get("content", ""),
                fetch_method="firecrawl",
                fetch_reason=result.get("reason", "firecrawl_ok")
            )
            
        except Exception as e:
            # Record failure
            circuit_breaker.record_failure()
            
            logger.error(f"Firecrawl error: {e}")
            return PageData(
                url=original_url, final_url=normalized_url,
                normalized_url=normalized_url,
                fetch_method="firecrawl", fetch_reason="firecrawl_error",
                error=str(e)
            )
