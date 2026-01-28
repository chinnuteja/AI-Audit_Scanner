"""
LLMs.txt Collector - Fetch llms.txt for AI discoverability.
"""
import httpx
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

from app.logger import logger


@dataclass
class LlmsTxtData:
    """Parsed llms.txt data."""
    exists: bool = False
    content: str = ""
    has_description: bool = False
    has_contact: bool = False
    error: Optional[str] = None


class LlmsTxtCollector:
    """Fetches and parses llms.txt."""
    
    async def fetch(self, base_url: str) -> LlmsTxtData:
        """Fetch llms.txt from the domain."""
        llms_url = urljoin(base_url, '/llms.txt')
        
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(llms_url)
                
                if response.status_code == 200:
                    content = response.text
                    return self._parse(content)
                else:
                    return LlmsTxtData(exists=False)
                    
        except Exception as e:
            logger.debug(f"llms.txt not found: {e}")
            return LlmsTxtData(exists=False, error=str(e))
    
    def _parse(self, content: str) -> LlmsTxtData:
        """Parse llms.txt content."""
        data = LlmsTxtData(exists=True, content=content)
        
        lower = content.lower()
        data.has_description = 'description' in lower or len(content) > 50
        data.has_contact = 'contact' in lower or '@' in content
        
        return data
