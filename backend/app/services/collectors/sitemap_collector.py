"""
Sitemap Collector - Detect and parse sitemap.xml.

Checks:
- Sitemap URL from robots.txt
- Common sitemap locations
- Basic sitemap structure
"""

import re
import httpx
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from app.logger import logger


@dataclass
class SitemapData:
    """Parsed sitemap data."""
    exists: bool = False
    url: Optional[str] = None
    source: str = ""  # 'robots', 'common_path', 'not_found'
    
    # Stats
    url_count: int = 0
    is_index: bool = False  # Is it a sitemap index?
    
    error: Optional[str] = None


class SitemapCollector:
    """Collector for sitemap.xml."""
    
    COMMON_PATHS = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/sitemaps.xml",
    ]
    
    async def fetch(self, url: str, robots_content: str = None) -> SitemapData:
        """Detect and fetch sitemap.
        
        Args:
            url: Any URL on the domain
            robots_content: Optional robots.txt content to check for sitemap directive
            
        Returns:
            SitemapData
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check robots.txt first
        if robots_content:
            sitemap_url = self._extract_from_robots(robots_content, base_url)
            if sitemap_url:
                result = await self._fetch_sitemap(sitemap_url)
                if result.exists:
                    result.source = "robots"
                    return result
        
        # Try common paths
        for path in self.COMMON_PATHS:
            sitemap_url = urljoin(base_url, path)
            result = await self._fetch_sitemap(sitemap_url)
            if result.exists:
                result.source = "common_path"
                return result
        
        return SitemapData(exists=False, source="not_found")
    
    def _extract_from_robots(self, robots_content: str, base_url: str) -> Optional[str]:
        """Extract sitemap URL from robots.txt."""
        for line in robots_content.split('\n'):
            line = line.strip().lower()
            if line.startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                # Handle relative URLs
                if not sitemap_url.startswith('http'):
                    sitemap_url = urljoin(base_url, sitemap_url)
                return sitemap_url
        return None
    
    async def _fetch_sitemap(self, sitemap_url: str) -> SitemapData:
        """Fetch and parse a sitemap URL."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(sitemap_url)
                
                if response.status_code != 200:
                    return SitemapData(exists=False)
                
                content = response.text
                
                # Check if it's valid XML sitemap
                if '<urlset' not in content and '<sitemapindex' not in content:
                    return SitemapData(exists=False)
                
                # Parse basic info
                is_index = '<sitemapindex' in content
                url_count = len(re.findall(r'<loc>', content))
                
                return SitemapData(
                    exists=True,
                    url=sitemap_url,
                    is_index=is_index,
                    url_count=url_count
                )
                
        except Exception as e:
            logger.warning(f"Error fetching sitemap {sitemap_url}: {e}")
            return SitemapData(exists=False, error=str(e))
