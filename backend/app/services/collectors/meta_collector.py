"""
Meta Collector - Extract meta tags and content from HTML.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from app.logger import logger


@dataclass
class MetaData:
    """Extracted metadata from a page."""
    title: str = ""
    title_length: int = 0
    description: str = ""
    description_length: int = 0
    h1_tags: List[str] = field(default_factory=list)
    h2_tags: List[str] = field(default_factory=list)
    h3_tags: List[str] = field(default_factory=list)
    canonical: str = ""
    og_tags: Dict[str, str] = field(default_factory=dict)
    twitter_tags: Dict[str, str] = field(default_factory=dict)
    word_count: int = 0
    internal_links: int = 0
    external_links: int = 0
    images_total: int = 0
    images_with_alt: int = 0
    lang: str = ""
    viewport: str = ""
    robots_meta: str = ""
    text_content: str = ""


class MetaCollector:
    """Collects metadata from HTML content."""
    
    def collect(self, html: str, url: str) -> MetaData:
        """Extract metadata from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            data = MetaData()
            
            # Title
            title_tag = soup.find('title')
            if title_tag:
                data.title = title_tag.get_text(strip=True)
                data.title_length = len(data.title)
            
            # Meta description
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                data.description = desc_tag.get('content', '')
                data.description_length = len(data.description)
            
            # Headings
            data.h1_tags = [h.get_text(strip=True) for h in soup.find_all('h1')]
            data.h2_tags = [h.get_text(strip=True) for h in soup.find_all('h2')]
            data.h3_tags = [h.get_text(strip=True) for h in soup.find_all('h3')]
            
            # Canonical
            canonical_tag = soup.find('link', rel='canonical')
            if canonical_tag:
                data.canonical = canonical_tag.get('href', '')
            
            # OpenGraph
            for og in soup.find_all('meta', property=re.compile(r'^og:')):
                prop = og.get('property', '').replace('og:', '')
                data.og_tags[prop] = og.get('content', '')
            
            # Twitter Cards
            for tw in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
                name = tw.get('name', '').replace('twitter:', '')
                data.twitter_tags[name] = tw.get('content', '')
            
            # Body text
            body = soup.find('body')
            if body:
                # Remove script and style
                for tag in body.find_all(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                text = body.get_text(separator=' ', strip=True)
                data.text_content = text
                data.word_count = len(text.split())
            
            # Links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith(('http://', 'https://')):
                    if url in href:
                        data.internal_links += 1
                    else:
                        data.external_links += 1
                elif href.startswith('/'):
                    data.internal_links += 1
            
            # Images
            images = soup.find_all('img')
            data.images_total = len(images)
            data.images_with_alt = sum(1 for img in images if img.get('alt', '').strip())
            
            # HTML lang
            html_tag = soup.find('html')
            if html_tag:
                data.lang = html_tag.get('lang', '')
            
            # Viewport
            viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
            if viewport_tag:
                data.viewport = viewport_tag.get('content', '')
            
            # Robots meta
            robots_tag = soup.find('meta', attrs={'name': 'robots'})
            if robots_tag:
                data.robots_meta = robots_tag.get('content', '')
            
            return data
            
        except Exception as e:
            logger.error(f"MetaCollector error: {e}")
            return MetaData()
