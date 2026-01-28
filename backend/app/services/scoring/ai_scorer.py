"""
AI Scorer - Evaluates AI readiness and discoverability.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from app.services.scoring.models import Check

@dataclass
class AIResult:
    """Result of AI scoring."""
    score: int
    checks: List[Check]


class AIScorer:
    """Scores AI optimization."""
    
    def score(
        self,
        ai_bots_allowed: List[str],
        ai_bots_blocked: List[str],
        llms_txt_exists: bool,
        llms_txt_quality: int,
        has_schema: bool,
        schema_types: List[str],
        has_og_tags: bool,
        has_twitter_cards: bool,
        has_faq_schema: bool,
        word_count: int
    ) -> AIResult:
        """
        Calculate AI score.
        Uses STRICT scoring (sum of awarded points).
        """
        from app.services.scoring.weights import AI_WEIGHTS as W
        
        checks = []
        
        # Helper to add check
        def add_check(id, cat, name, pts, max_pts, condition, evidence_pass, evidence_fail, fix="", severity="P2"):
            if condition:
                checks.append(Check(id, cat, name, "pass", pts, max_pts, evidence_pass, "", "high", severity))
            else:
                checks.append(Check(id, cat, name, "fail", 0, max_pts, evidence_fail, fix, "high", severity))

        # --- 1. AI Crawler Access (25 pts) ---
        # W.robots_ai_bots
        
        major_bots = ["GPTBot", "CCBot", "Google-Extended", "ClaudeBot"]
        
        # "Allowed" if wildcard or explicit allow
        # RobotsCollector usually implies wildcard if not blocked.
        # Strict check: are any major bots in blocked list?
        
        blocked_major = [b for b in major_bots if b in ai_bots_blocked]
        
        if not blocked_major:
            checks.append(Check("ai_access", "ai_crawler", "AI Crawler Access", "pass", W.robots_ai_bots, W.robots_ai_bots, "All major AI bots allowed", "", "high", "P0"))
        elif len(blocked_major) < len(major_bots):
            checks.append(Check("ai_access", "ai_crawler", "AI Crawler Access", "partial", W.robots_ai_bots // 2, W.robots_ai_bots, f"Blocked: {', '.join(blocked_major)}", "Allow GPTBot/CCBot", "high", "P1"))
        else:
            checks.append(Check("ai_access", "ai_crawler", "AI Crawler Access", "fail", 0, W.robots_ai_bots, "Major AI bots blocked", "Update robots.txt to allow AI", "high", "P1"))

        # --- 2. llms.txt (15 pts) ---
        # Existence (5) + Quality (10)
        
        if llms_txt_exists:
            checks.append(Check("ai_llms_exist", "llms_txt", "llms.txt Found", "pass", W.llms_txt_exists, W.llms_txt_exists, "File exists", "", "high", "P2"))
            
            # Quality score (0-10)
            # Assuming quality is 0-5 from input -> scale to 0-10
            q_val = min(llms_txt_quality * 2, 10) 
            q_pts = min(q_val, W.llms_txt_quality)
            
            if q_pts >= 8:
                 checks.append(Check("ai_llms_quality", "llms_txt", "llms.txt Quality", "pass", q_pts, W.llms_txt_quality, "High quality content", "", "high", "P2"))
            elif q_pts >= 1:
                 checks.append(Check("ai_llms_quality", "llms_txt", "llms.txt Quality", "partial", q_pts, W.llms_txt_quality, "Basic content", "Add more context/files", "medium", "P2"))
            else:
                 checks.append(Check("ai_llms_quality", "llms_txt", "llms.txt Quality", "fail", 0, W.llms_txt_quality, "Empty/Low quality", "Improve content description", "medium", "P2"))
        else:
             add_check("ai_llms_exist", "llms_txt", "llms.txt Found", 0, W.llms_txt_exists, False, "", "Missing llms.txt", "Create /llms.txt", "P2")
             checks.append(Check("ai_llms_quality", "llms_txt", "llms.txt Quality", "skip", 0, W.llms_txt_quality, "N/A", "", "medium", "P3"))

        # --- 3. Structured Data (30 pts) ---
        # Schema Exists (12) + Types (18)
        
        add_check("ai_schema_exist", "schema", "Schema Markup", W.schema_exists, W.schema_exists, has_schema, "JSON-LD detected", "No structured data", "Add JSON-LD schema", "P1")
        
        if has_schema:
            # Richness check: FAQ, Product, etc?
            # Basic logic: count types or check specific meaningful types.
            # meaningful = Organization, Product, Article, FAQPage etc.
            count = len(schema_types)
            has_rich = has_faq_schema or "Product" in schema_types or "Review" in schema_types
            
            if has_rich or count >= 2:
                pts = W.schema_types
                status = "pass"
                evidence = f"Rich schema found ({', '.join(schema_types[:3])})"
            else:
                pts = W.schema_types // 2
                status = "partial"
                evidence = f"Basic schema found ({', '.join(schema_types[:3])})"
                
            checks.append(Check("ai_schema_types", "schema", "Schema Types", status, pts, W.schema_types, evidence, "Add FAQ/Product schema", "high", "P2"))
        else:
             checks.append(Check("ai_schema_types", "schema", "Schema Types", "fail", 0, W.schema_types, "No schema", "Add rich snippets", "high", "P2"))

        # --- 4. Social Previews (15 pts) ---
        # OG (8) + Twitter (7)
        
        add_check("ai_og", "social", "OpenGraph Tags", W.og_tags, W.og_tags, has_og_tags, "OG tags present", "Missing OG tags", "Add og:title, og:image", "P2")
        add_check("ai_twitter", "social", "Twitter Cards", W.twitter_cards, W.twitter_cards, has_twitter_cards, "Twitter card present", "Missing Twitter card", "Add twitter:card", "P2")

        # --- 5. Extractability (15 pts) ---
        # Based on word count (simplified proxy for text-to-html ratio)
        
        if word_count >= 500:
             checks.append(Check("ai_extract", "extractability", "Content Extractability", "pass", W.extractability, W.extractability, f"High volume ({word_count} words)", "", "high", "P2"))
        elif word_count >= 200:
             checks.append(Check("ai_extract", "extractability", "Content Extractability", "partial", W.extractability // 2, W.extractability, "Moderate volume", "Add more HTML text", "medium", "P2"))
        else:
             checks.append(Check("ai_extract", "extractability", "Content Extractability", "fail", 0, W.extractability, "Low text volume", "Ensure content is machine-readable", "high", "P1"))

        # Calculate STRICT score
        final_score = sum(c.points_awarded for c in checks)
        
        return AIResult(score=int(final_score), checks=checks)

