"""
Technical Scorer - Evaluates technical SEO health.
"""
from dataclasses import dataclass, field
from typing import List, Optional

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
    severity: str = "P2"

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
        """
        checks = []
        total_points = 0
        max_points = 0
        
        # Helper to add check
        def add_check(id, cat, name, pts, max_pts, condition, evidence_pass, evidence_fail, fix="", severity="P2"):
            nonlocal total_points, max_points
            max_points += max_pts
            if condition:
                total_points += pts
                checks.append(Check(id, cat, name, "pass", pts, max_pts, evidence_pass, "", "high", severity))
            else:
                checks.append(Check(id, cat, name, "fail", 0, max_pts, evidence_fail, fix, "high", severity))

        # 1. SSL/Status (15 pts)
        if status_code and 200 <= status_code < 300:
            add_check("tech_status", "crawlability", "HTTP Status", 10, 10, True, f"Status {status_code}", f"Status {status_code}", "Fix server errors", "P0")
        else:
            add_check("tech_status", "crawlability", "HTTP Status", 10, 10, False, "", f"Status {status_code}", "Ensure site returns 200 OK", "P0")
            
        add_check("tech_https", "performance", "HTTPS", 5, 5, is_https, "Uses HTTPS", "Not using HTTPS", "Enable SSL/HTTPS", "P0")

        # 2. Indexability (20 pts)
        add_check("tech_noindex", "crawlability", "Indexability", 10, 10, not has_noindex, "Page is indexable", "noindex tag detected", "Remove noindex tag if page should be ranked", "P0")
        add_check("tech_canonical", "crawlability", "Canonical Tag", 5, 5, has_canonical, "Canonical tag present", "Missing canonical tag", "Add self-referencing canonical", "P2")
        if has_canonical:
            add_check("tech_canonical_match", "crawlability", "Canonical Match", 5, 5, canonical_matches_url, "Canonical matches URL", "Canonical points elsewhere", "Ensure canonical points to this page", "P2")

        # 3. Core Web Vitals / Performance (20 pts)
        if performance_score is not None:
            if performance_score >= 90:
                checks.append(Check("tech_perf", "performance", "Performance Score", "pass", 20, 20, f"Score: {performance_score}", "", "high", "P1"))
                total_points += 20
                max_points += 20
            elif performance_score >= 50:
                checks.append(Check("tech_perf", "performance", "Performance Score", "partial", 10, 20, f"Score: {performance_score}", "Optimize images and scripts", "high", "P1"))
                total_points += 10
                max_points += 20
            else:
                checks.append(Check("tech_perf", "performance", "Performance Score", "fail", 0, 20, f"Score: {performance_score}", "Critical speed checks needed", "high", "P1"))
                max_points += 20
        else:
            checks.append(Check("tech_perf", "performance", "Performance Score", "skip", 0, 0, "Not checked", "", "high", "P2"))

        add_check("tech_viewport", "performance", "Mobile Viewport", 10, 10, has_viewport, "Viewport tag present", "Missing viewport tag", "Add <meta name='viewport'>", "P1")

        # 4. Structure (15 pts)
        add_check("tech_title", "hygiene", "Title Tag", 5, 5, has_title, "Title tag present", "Missing title tag", "Add title tag", "P1")
        add_check("tech_h1", "hygiene", "H1 Tag", 5, 5, h1_count == 1, f"Found {h1_count} H1 tags", f"Found {h1_count} H1 tags", "Use exactly one H1 tag per page", "P2")
        add_check("tech_headings", "hygiene", "Heading Hierarchy", 5, 5, heading_order_valid, "Valid heading structure", "Skipped heading levels", "Ensure H1 -> H2 -> H3 order", "P2")

        # 5. Global (20 pts)
        add_check("tech_robots", "crawlability", "robots.txt", 5, 5, has_robots_txt, "robots.txt found", "Missing robots.txt", "Add robots.txt", "P2")
        add_check("tech_sitemap", "crawlability", "Sitemap", 5, 5, has_sitemap, "Sitemap found", "Missing sitemap", "Submit sitemap to search engines", "P2")
        add_check("tech_lang", "hygiene", "HTML Lang", 5, 5, has_html_lang, "Lang attribute present", "Missing lang attribute", "Add lang='en' to <html>", "P2")
        add_check("tech_charset", "hygiene", "Charset", 5, 5, has_charset, "Charset defined", "Missing charset", "Add <meta charset='utf-8'>", "P2")

        # Calculate percentage score
        final_score = int((total_points / max_points) * 100) if max_points > 0 else 0
        
        return TechnicalResult(score=final_score, checks=checks)

