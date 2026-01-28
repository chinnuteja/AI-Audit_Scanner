"""
Schema Collector - Extract JSON-LD structured data from HTML.

Extracts:
- Schema.org JSON-LD blocks
- Schema types (Organization, Product, Article, FAQPage, etc.)
- Validates basic structure
"""

import json
from typing import Optional
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

from app.logger import logger


@dataclass
class SchemaItem:
    """Single JSON-LD schema block."""
    type: str
    data: dict
    valid: bool = True
    error: Optional[str] = None


@dataclass
class SchemaData:
    """All structured data from page."""
    schemas: list[SchemaItem] = field(default_factory=list)
    
    @property
    def types(self) -> list[str]:
        """Get all schema types found."""
        return [s.type for s in self.schemas if s.valid]
    
    @property
    def has_organization(self) -> bool:
        return "Organization" in self.types or "LocalBusiness" in self.types
    
    @property
    def has_product(self) -> bool:
        return "Product" in self.types
    
    @property
    def has_article(self) -> bool:
        return any(t in self.types for t in ["Article", "NewsArticle", "BlogPosting"])
    
    @property
    def has_faq(self) -> bool:
        return "FAQPage" in self.types
    
    @property
    def has_breadcrumb(self) -> bool:
        return "BreadcrumbList" in self.types
    
    @property
    def has_any(self) -> bool:
        return len(self.schemas) > 0


class SchemaCollector:
    """Collector for JSON-LD structured data."""
    
    def collect(self, html: str) -> SchemaData:
        """Extract all JSON-LD schemas from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            SchemaData with all found schemas
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            schema_data = SchemaData()
            
            # Find all JSON-LD script tags
            scripts = soup.find_all('script', type='application/ld+json')
            
            for script in scripts:
                try:
                    if not script.string:
                        continue
                    
                    data = json.loads(script.string)
                    
                    # Handle @graph arrays
                    if isinstance(data, dict) and "@graph" in data:
                        for item in data["@graph"]:
                            schema_data.schemas.append(self._parse_schema(item))
                    elif isinstance(data, list):
                        for item in data:
                            schema_data.schemas.append(self._parse_schema(item))
                    else:
                        schema_data.schemas.append(self._parse_schema(data))
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON-LD: {e}")
                    schema_data.schemas.append(SchemaItem(
                        type="unknown",
                        data={},
                        valid=False,
                        error=f"Invalid JSON: {str(e)[:100]}"
                    ))
            
            logger.debug(f"Found {len(schema_data.schemas)} schemas: {schema_data.types}")
            return schema_data
            
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
            return SchemaData()
    
    def _parse_schema(self, data: dict) -> SchemaItem:
        """Parse a single schema object."""
        if not isinstance(data, dict):
            return SchemaItem(type="unknown", data={}, valid=False, error="Not a dict")
        
        schema_type = data.get("@type", "unknown")
        
        # Handle array of types
        if isinstance(schema_type, list):
            schema_type = schema_type[0] if schema_type else "unknown"
        
        return SchemaItem(type=schema_type, data=data, valid=True)
