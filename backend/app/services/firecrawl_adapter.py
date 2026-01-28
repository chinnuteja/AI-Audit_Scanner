"""
Firecrawl Adapter - Isolated adapter for Firecrawl API with cost controls.

Handles:
- JS-heavy pages
- PDFs
- Cookie walls
- Rate limiting
- Retry logic
"""

import asyncio
from typing import Optional

from app.config import settings
from app.logger import logger


class FirecrawlAdapter:
    """Adapter for Firecrawl API with cost controls and error handling."""
    
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.timeout = settings.FIRECRAWL_TIMEOUT
        self.max_retries = 1  # Expensive, use sparingly
        
    async def scrape(self, url: str) -> dict:
        """Scrape page using Tiered Strategy (Free -> Paid).
        
        1. Try simple HTTPX (Free)
        2. If blocked/empty, use Firecrawl (Paid)
        
        Args:
            url: URL to scrape
            
        Returns:
            Dict with content, reason, final_url, status_code, content_type
        """
        logger.debug(f"Firecrawl scrape called for {url}")
        
        # --- TIER 1: FREE SCRAPER (HTTPX) ---
        free_result = await self._scrape_free(url)
        content = free_result.get("content", "")
        
        # Check if free scrape successfully got meaningful content
        is_blocked = "403 Forbidden" in content or "Access Denied" in content or "Cloudflare" in content
        is_short = len(content) < 1000
        
        if free_result.get("success") and not is_blocked and not is_short:
            logger.info(f"Free scrape successful for {url} (Length: {len(content)})")
            return {
                "content": content,
                "reason": "free_scrape_success",
                "final_url": url,
                "status_code": free_result.get("status_code", 200),
                "content_type": free_result.get("content_type", "text/html")
            }
        
        logger.info(f"Free scrape insufficient for {url}. Upgrading to Firecrawl...")

        # --- TIER 2: PAID SCRAPER (FIRECRAWL) ---
        if not self.api_key:
            logger.warning("Firecrawl API key not configured")
            return self._fallback_response(url, "firecrawl_no_api_key")
        
        # Try Firecrawl with retry
        for attempt in range(self.max_retries + 1):
            try:
                result = await self._firecrawl_request(url)
                
                # Success
                if result.get("success"):
                    content = result.get("content", "")
                    
                    # Detect content type
                    if result.get("metadata", {}).get("contentType", "").startswith("application/pdf"):
                        reason = "firecrawl_pdf"
                    elif len(content) > 1000 and "<script" in content.lower():
                        reason = "firecrawl_used_js"
                    else:
                        reason = "firecrawl_ok"
                    
                    logger.info(f"Firecrawl successful for {url} (reason: {reason})")
                    
                    return {
                        "content": content,
                        "reason": reason,
                        "final_url": result.get("metadata", {}).get("url", url),
                        "status_code": result.get("metadata", {}).get("statusCode", 200),
                        "content_type": result.get("metadata", {}).get("contentType", "text/html")
                    }
                
                # Rate limited
                elif result.get("error") == "rate_limit":
                    if attempt < self.max_retries:
                        backoff = 5
                        logger.warning(f"Firecrawl rate limited for {url}, retrying in {backoff}s")
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        return self._fallback_response(url, "firecrawl_rate_limited")
                
                # Other error
                else:
                    logger.warning(f"Firecrawl error for {url}: {result.get('error')}")
                    return self._fallback_response(url, f"firecrawl_error_{result.get('error', 'unknown')}")
                    
            except asyncio.TimeoutError:
                if attempt < self.max_retries:
                    logger.warning(f"Firecrawl timeout for {url}, retrying")
                    continue
                else:
                    return self._fallback_response(url, "firecrawl_timeout")
            except Exception as e:
                logger.error(f"Firecrawl exception for {url}: {e}")
                return self._fallback_response(url, "firecrawl_exception")
        
        return self._fallback_response(url, "firecrawl_failed")

    async def _scrape_free(self, url: str) -> dict:
        """Attempt free scraping using HTTPX."""
        import httpx
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                
                if resp.status_code == 200:
                    return {
                        "success": True,
                        "content": resp.text,
                        "status_code": resp.status_code,
                        "content_type": resp.headers.get("content-type", "text/html")
                    }
                else:
                    return {"success": False, "status_code": resp.status_code}
        except Exception as e:
            logger.warning(f"Free scrape error for {url}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _firecrawl_request(self, url: str) -> dict:
        """Make actual Firecrawl API request."""
        try:
            # Import Firecrawl SDK (handle v0 and v1)
            AppClass = None
            try:
                from firecrawl import Firecrawl
                AppClass = Firecrawl
            except ImportError:
                try:
                    from firecrawl import FirecrawlApp
                    AppClass = FirecrawlApp
                except ImportError:
                    pass

            if not AppClass:
                logger.warning("firecrawl-py not installed")
                return {"success": False, "error": "sdk_not_installed"}
            
            app = AppClass(api_key=self.api_key)
            
            # Prepare params
            params = {
                'formats': ['markdown', 'html'],
                'only_main_content': False,
                'wait_for': 5000
            }

            # Execute scrape
            method = getattr(app, 'scrape', None) or getattr(app, 'scrape_url', None)
            if not method:
                return {"success": False, "error": "unknown_sdk_method"}
            
            result = await asyncio.to_thread(method, url, **params)
            
            # Normalize result
            data = {}
            if isinstance(result, dict):
                data = result.get('data', result)
            elif hasattr(result, "model_dump"):
                data = result.model_dump()
            elif hasattr(result, "dict"):
                data = result.dict()
            elif hasattr(result, "__dict__"):
                data = result.__dict__
            
            if not isinstance(data, dict):
                data = {'markdown': str(result)}

            content = data.get("html") or data.get("markdown") or ""
            
            return {
                "success": True,
                "content": content,
                "metadata": {
                    "url": data.get("metadata", {}).get("url", url),
                    "statusCode": data.get("metadata", {}).get("statusCode", 200),
                    "contentType": data.get("metadata", {}).get("contentType", "text/html")
                }
            }
            
        except ImportError:
            logger.warning("firecrawl-py not installed, using fallback")
            return {"success": False, "error": "sdk_not_installed"}
        except Exception as e:
            logger.error(f"Firecrawl API error: {e}")
            return {"success": False, "error": str(e)}
    
    def _fallback_response(self, url: str, reason: str) -> dict:
        """Generate fallback response when Firecrawl fails."""
        logger.warning(f"Firecrawl fallback for {url} (reason: {reason})")
        
        return {
            "content": f"<html><head><title>Fetch Failed</title></head><body><p>Failed to fetch: {reason}</p></body></html>",
            "reason": reason,
            "final_url": url,
            "status_code": None,
            "content_type": "text/html"
        }
