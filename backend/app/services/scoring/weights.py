"""
Scoring Weights Configuration - v1.1

Aligned with industry standards (RankZero, Ahrefs-style).
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Check:
    """Individual audit check result."""
    id: str
    category: str
    name: str
    status: str  # pass, fail, partial, skip, info
    points_awarded: float
    points_possible: float
    evidence: str = ""
    how_to_fix: str = ""
    importance: str = "high"


@dataclass
class CategoryWeights:
    """Overall category weights (must sum to 100)."""
    technical: int = 35   # Industry standard: Technical first
    content: int = 35     # Content quality equally important
    ai_seo: int = 30      # AI readiness (lower than v1.0)


@dataclass
class TechnicalWeights:
    """Technical SEO check weights (must sum to 100)."""
    # Crawlability & Indexability (40 pts)
    status_code: int = 10
    redirects: int = 5
    canonical: int = 8
    meta_robots: int = 7
    sitemap: int = 5
    robots_txt: int = 5   # NEW: robots.txt existence
    
    # Performance & UX (30 pts)
    performance_score: int = 12
    mobile_friendly: int = 10
    https: int = 8
    
    # Hygiene & Basics (30 pts)
    title: int = 10
    meta_description: int = 8
    h1: int = 7
    heading_hierarchy: int = 5


@dataclass
class AIWeights:
    """AI SEO check weights (must sum to 100)."""
    # AI Crawler Access (25 pts) - reduced
    robots_ai_bots: int = 25
    
    # llms.txt (15 pts) - NOW BONUS, not penalty
    llms_txt_exists: int = 5      # Reduced: optional bonus
    llms_txt_quality: int = 10    # Reduced
    
    # Structured Data (30 pts) - increased importance
    schema_exists: int = 12
    schema_types: int = 18
    
    # Social Previews (15 pts) - increased
    og_tags: int = 8
    twitter_cards: int = 7
    
    # Extractability (15 pts) - increased
    extractability: int = 15


@dataclass
class ContentWeights:
    """Content check weights (must sum to 100)."""
    # Clarity & Intent (20 pts)
    clarity: int = 20
    
    # Structure & Readability (20 pts)
    heading_structure: int = 10
    word_count: int = 5
    readability: int = 5
    
    # Completeness (10 pts)
    internal_links: int = 10
    
    # Freshness (15 pts)
    freshness: int = 15
    
    # Trust & Authenticity (35 pts)
    trust_auth: int = 35


# Default weight instances
CATEGORY_WEIGHTS = CategoryWeights()
TECHNICAL_WEIGHTS = TechnicalWeights()
AI_WEIGHTS = AIWeights()
CONTENT_WEIGHTS = ContentWeights()

# Scoring version
SCORING_VERSION = "2.0-PRO"

# --- Validation (Prevent Drift) ---
def _validate_weights():
    """Ensure all weight categories sum to exactly 100."""
    # 1. Category Weights
    total_cat = CATEGORY_WEIGHTS.technical + CATEGORY_WEIGHTS.content + CATEGORY_WEIGHTS.ai_seo
    if total_cat != 100:
        raise ValueError(f"CRITICAL: Category weights sum to {total_cat}, expected 100")
        
    # 2. Technical Weights
    w_tech = TECHNICAL_WEIGHTS
    total_tech = (w_tech.status_code + w_tech.redirects + w_tech.canonical + 
                  w_tech.meta_robots + w_tech.sitemap + w_tech.robots_txt +
                  w_tech.performance_score + w_tech.mobile_friendly + w_tech.https +
                  w_tech.title + w_tech.meta_description + w_tech.h1 + w_tech.heading_hierarchy)
    if total_tech != 100:
        raise ValueError(f"CRITICAL: Technical weights sum to {total_tech}, expected 100")

    # 3. Content Weights
    w_con = CONTENT_WEIGHTS
    total_con = (w_con.clarity + w_con.heading_structure + w_con.word_count + 
                 w_con.readability + w_con.internal_links + w_con.freshness + 
                 w_con.trust_auth)
    if total_con != 100:
        raise ValueError(f"CRITICAL: Content weights sum to {total_con}, expected 100")

    # 4. AI Weights
    w_ai = AI_WEIGHTS
    total_ai = (w_ai.robots_ai_bots + w_ai.llms_txt_exists + w_ai.llms_txt_quality +
                w_ai.schema_exists + w_ai.schema_types + w_ai.og_tags + 
                w_ai.twitter_cards + w_ai.extractability)
    if total_ai != 100:
        raise ValueError(f"CRITICAL: AI weights sum to {total_ai}, expected 100")

_validate_weights()
