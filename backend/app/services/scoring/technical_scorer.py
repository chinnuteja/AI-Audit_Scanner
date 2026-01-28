"""
Technical Scorer - Evaluates technical SEO health.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from app.services.scoring.models import Check

@dataclass
class TechnicalResult:
    """Result of technical scoring."""
    score: int
    checks: List[Check]

class TechnicalScorer:
    """Scores technical health."""
    
    def score(
        self, 
        status_code: Optional[int],
        redirect_count: int,
        has_canonical: bool,
        canonical_matches_url: bool,
        has_noindex: bool,
        has_sitemap: bool,
        has_robots_txt: bool,
        performance_score: Optional[int],
        has_viewport: bool,
        is_https: bool,
        has_title: bool,
        title_length: int,
        has_meta_description: bool,
        meta_description_length: int,
        h1_count: int,
        heading_order_valid: bool,
        has_charset: bool,
        has_html_lang: bool,
        total_images: int,
        images_with_alt: int,
        internal_links: int,
        external_links: int
    ) -> TechnicalResult:
        """
        Calculate Technical score based on extracted features.
        Uses STRICT scoring (sum of awarded points) with no normalization drift.
        """
        from app.services.scoring.weights import TECHNICAL_WEIGHTS as W
        
        checks = []
        
        # Helper to add check
        def add_check(id, cat, name, pts, max_pts, condition, evidence_pass, evidence_fail, fix="", severity="P2"):
            if condition:
                checks.append(Check(id, cat, name, "pass", pts, max_pts, evidence_pass, "", "high", severity))
            else:
                checks.append(Check(id, cat, name, "fail", 0, max_pts, evidence_fail, fix, "high", severity))

        # --- 1. Crawlability & Indexability (40 pts) ---
        
        # Status Code (10)
        status_ok = status_code and 200 <= status_code < 300
        add_check(
            "tech_status", "crawlability", "HTTP Status", 
            W.status_code, W.status_code, 
            status_ok, 
            f"Status {status_code}", f"Status {status_code}", 
            "Ensure site returns 200 OK", "P0"
        )
        
        # Redirects (5)
        # 0 is perfect, 1 is okay/partial, >1 is bad
        if redirect_count == 0:
            add_check("tech_redirects", "crawlability", "Redirect Chain", W.redirects, W.redirects, True, f"No redirects", "", "", "P2")
        elif redirect_count == 1:
             # Strict: 1 redirect is Partial (approx 40% points -> 2/5)
             pts_partial = int(W.redirects * 0.4) 
             checks.append(Check("tech_redirects", "crawlability", "Redirect Chain", "partial", pts_partial, W.redirects, f"{redirect_count} redirect(s)", "Reduce redirect chain length", "medium", "P2"))
        else:
             add_check("tech_redirects", "crawlability", "Redirect Chain", W.redirects, W.redirects, False, "", f"{redirect_count} redirects detected", "Remove unnecessary redirects", "P2")

        # Canonical (8) - Split 4/4
        pts_canon = W.canonical // 2
        add_check("tech_canonical", "crawlability", "Canonical Tag", pts_canon, pts_canon, has_canonical, "Present", "Missing", "Add canonical tag", "P2")
        
        if has_canonical:
            add_check("tech_canonical_match", "crawlability", "Canonical Match", pts_canon, pts_canon, canonical_matches_url, "Matches URL", "Points different URL", "Ensure canonical is self-referencing if intended", "P2")
        else:
             # If missing canonical, auto-fail match check too (0 points)
             checks.append(Check("tech_canonical_match", "crawlability", "Canonical Match", "fail", 0, pts_canon, "Missing canonical", "Add canonical tag first", "high", "P2"))

        # Meta Robots (7) - tech_noindex
        # We want indexable pages generally
        add_check("tech_noindex", "crawlability", "Indexability", W.meta_robots, W.meta_robots, not has_noindex, "Indexable", "Noindex detected", "Remove noindex tag", "P0")

        # Sitemap (5)
        add_check("tech_sitemap", "crawlability", "Sitemap", W.sitemap, W.sitemap, has_sitemap, "Found", "Missing", "Submit sitemap", "P2")

        # Robots.txt (5)
        add_check("tech_robots", "crawlability", "robots.txt", W.robots_txt, W.robots_txt, has_robots_txt, "Found", "Missing", "Add robots.txt", "P2")

        # --- 2. Performance & UX (30 pts) ---

        # Performance Score (12)
        if performance_score is not None:
            if performance_score >= 90:
                checks.append(Check("tech_perf", "performance", "Performance Score", "pass", W.performance_score, W.performance_score, f"Score: {performance_score}", "", "high", "P1"))
            elif performance_score >= 50:
                checks.append(Check("tech_perf", "performance", "Performance Score", "partial", W.performance_score // 2, W.performance_score, f"Score: {performance_score}", "Optimize LCP/CLS", "high", "P1"))
            else:
                checks.append(Check("tech_perf", "performance", "Performance Score", "fail", 0, W.performance_score, f"Score: {performance_score}", "Critical optimization needed", "high", "P1"))
        else:
             checks.append(Check("tech_perf", "performance", "Performance Score", "skip", 0, W.performance_score, "Not available", "Check api key", "high", "P2"))

        # Mobile Friendly (10) - tech_viewport
        add_check("tech_viewport", "performance", "Mobile Viewport", W.mobile_friendly, W.mobile_friendly, has_viewport, "Present", "Missing", "Add viewport meta tag", "P0")

        # HTTPS (8)
        add_check("tech_https", "performance", "HTTPS", W.https, W.https, is_https, "Secure", "Not Secure", "Enable SSL", "P0")

        # --- 3. Hygiene & Basics (30 pts) ---

        # Title (10)
        # Check existence AND length
        title_ok = has_title and 10 <= title_length <= 70
        if title_ok:
             add_check("tech_title", "hygiene", "Title Tag", W.title, W.title, True, f"Valid length ({title_length})", "", "", "P1")
        elif has_title:
             # Present but bad length - partial
             checks.append(Check("tech_title", "hygiene", "Title Tag", "partial", W.title // 2, W.title, f"Length: {title_length}", "Optimize length (10-70 chars)", "high", "P1"))
        else:
             add_check("tech_title", "hygiene", "Title Tag", W.title, W.title, False, "", "Missing title", "Add title tag", "P0")

        # Meta Description (8)
        desc_ok = has_meta_description and 50 <= meta_description_length <= 170
        if desc_ok:
            add_check("tech_meta_desc", "hygiene", "Meta Description", W.meta_description, W.meta_description, True, f"Valid length ({meta_description_length})", "", "", "P2")
        elif has_meta_description:
            checks.append(Check("tech_meta_desc", "hygiene", "Meta Description", "partial", W.meta_description // 2, W.meta_description, f"Length: {meta_description_length}", "Optimize length (50-170 chars)", "medium", "P2"))
        else:
            add_check("tech_meta_desc", "hygiene", "Meta Description", W.meta_description, W.meta_description, False, "", "Missing", "Add meta description", "P2")

        # H1 (7)
        add_check("tech_h1", "hygiene", "H1 Tag", W.h1, W.h1, h1_count == 1, f"Found {h1_count}", f"Found {h1_count}", "Use exactly one H1", "P2")

        # Heading Hierarchy (5)
        add_check("tech_headings", "hygiene", "Heading Structure", W.heading_hierarchy, W.heading_hierarchy, heading_order_valid, "Valid order", "Invalid order", "Fix H1->H2->H3 hierarchy", "P2")

        # --- Informational (0 pts) ---
        add_check("tech_lang", "hygiene", "HTML Lang", 0, 0, has_html_lang, "Present", "Missing", "Add lang attribute", "P3")
        add_check("tech_charset", "hygiene", "Charset", 0, 0, has_charset, "Present", "Missing", "Add charset meta tag", "P3")
        
        if total_images > 0:
            alt_ratio = images_with_alt / total_images
            add_check("tech_alt", "hygiene", "Image Alt Text", 0, 0, alt_ratio >= 0.8, f"{int(alt_ratio*100)}% have alt", "Missing alt text", "Add alt text to images", "P3")

        # Calculate STRICT score
        final_score = sum(c.points_awarded for c in checks)
        
        return TechnicalResult(score=int(final_score), checks=checks)

