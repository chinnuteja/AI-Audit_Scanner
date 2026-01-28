"""
Robots.txt Collector - Fetch and parse robots.txt.
"""
import httpx
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin

from app.logger import logger


@dataclass
class RobotsData:
    """Parsed robots.txt data."""
    exists: bool = False
    content: str = ""
    allows_all: bool = True
    disallow_rules: List[str] = field(default_factory=list)
    sitemaps: List[str] = field(default_factory=list)
    error: Optional[str] = None


class RobotsCollector:
    """Fetches and parses robots.txt."""
    
    async def fetch(self, base_url: str) -> RobotsData:
        """Fetch robots.txt from the domain."""
        robots_url = urljoin(base_url, '/robots.txt')
        
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(robots_url)
                
                if response.status_code == 200:
                    content = response.text
                    return self._parse(content)
                else:
                    return RobotsData(exists=False)
                    
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt: {e}")
            return RobotsData(exists=False, error=str(e))
    
    def _parse(self, content: str) -> RobotsData:
        """Parse robots.txt content."""
        data = RobotsData(exists=True, content=content)
        
        lines = content.split('\n')
        current_agent = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'user-agent':
                    current_agent = value
                elif key == 'disallow' and value:
                    data.disallow_rules.append(value)
                    if current_agent == '*' or current_agent is None:
                        data.allows_all = False
                elif key == 'sitemap':
                    data.sitemaps.append(value)
        
        return data
