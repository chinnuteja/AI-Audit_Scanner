"""
Application configuration using environment variables.
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Load .env file
load_dotenv()

@dataclass
class Settings:
    """Application settings."""
    APP_NAME: str = "Svata AI Auditor"
    
    # API Keys
    FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY", "")
    PAGESPEED_API_KEY: str = os.getenv("PAGESPEED_API_KEY", "")
    
    # Firecrawl settings
    FIRECRAWL_TIMEOUT: int = int(os.getenv("FIRECRAWL_TIMEOUT", "30"))
    FIRECRAWL_MAX_RETRIES: int = int(os.getenv("FIRECRAWL_MAX_RETRIES", "2"))
    
    # HTTP client settings
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "15"))
    HTTP_MAX_RETRIES: int = int(os.getenv("HTTP_MAX_RETRIES", "2"))
    HTTP_MAX_REDIRECTS: int = int(os.getenv("HTTP_MAX_REDIRECTS", "5"))
    
    # Performance
    PAGESPEED_ENABLED: bool = os.getenv("PAGESPEED_ENABLED", "true").lower() == "true"
    
    # CORS
    CORS_ORIGINS: List[str] = field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])

settings = Settings()

