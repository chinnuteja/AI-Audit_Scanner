"""
AI Scorer - Evaluates AI readiness and discoverability.
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
        
        Returns:
            AIResult with score and checks
        """
        checks = []
        total_points = 0
        max_points = 100
        
        # 1. AI Access (30 pts)
        # Check if major bots are allowed
        major_bots = ["GPTBot", "CCBot", "Google-Extended", "ClaudeBot"]
        allowed_count = 0
        blocked_count = 0
        
        # Determine strict status
        # If we have explicit allowed list (robots.txt exists), check it
        # Note: RobotsCollector logic usually returns 'allowed_bots' as wildcard ['*'] if allow all
        
        full_access = '*' in ai_bots_allowed or (len(ai_bots_blocked) == 0 and len(ai_bots_allowed) > 0)
        
        if full_access:
            total_points += 30
            checks.append(Check("ai_access", "ai_access", "AI Crawler Access", "pass", 30, 30, "All AI bots allowed", "", "high", "P0"))
        elif len(ai_bots_blocked) > 0:
            # Partial credit if some allowed
            total_points += 10
            checks.append(Check("ai_access", "ai_access", "AI Crawler Access", "partial", 10, 30, f"Some bots blocked: {', '.join(ai_bots_blocked[:3])}", "Allow GPTBot and CCBot", "high", "P1"))
        else:
             # Default fallback
             checks.append(Check("ai_access", "ai_access", "AI Crawler Access", "fail", 0, 30, "Crawler access unclear", "Check robots.txt", "high", "P1"))

        # 2. llms.txt (15 pts)
        if llms_txt_exists:
            score_llms = 10 + min(llms_txt_quality, 5) # Base 10 + quality bonus
            total_points += score_llms
            checks.append(Check("ai_llms_txt", "llms_txt", "llms.txt File", "pass", score_llms, 15, "llms.txt found", "", "medium", "P2"))
        else:
            checks.append(Check("ai_llms_txt", "llms_txt", "llms.txt File", "partial", 0, 15, "Missing llms.txt", "Create /llms.txt for AI context", "low", "P3")) # Optional-ish

        # 3. Schema & Semantics (25 pts)
        if has_schema:
            pts = 15
            evidence = f"Schema found: {', '.join(schema_types[:3])}"
            if has_faq_schema:
                pts += 10
                evidence += " (Includes FAQ)"
            
            total_points += pts
            checks.append(Check("ai_schema", "schema", "Schema Markup", "pass", pts, 25, evidence, "", "high", "P2"))
        else:
            checks.append(Check("ai_schema", "schema", "Schema Markup", "fail", 0, 25, "No structured data found", "Add JSON-LD schema", "high", "P2"))

        # 4. Social Context (15 pts) - OPG/Twitter act as proxies for AI context
        if has_og_tags and has_twitter_cards:
            total_points += 15
            checks.append(Check("ai_social", "social", "Social Context", "pass", 15, 15, "OG and Twitter tags present", "", "medium", "P2"))
        elif has_og_tags:
            total_points += 10
            checks.append(Check("ai_social", "social", "Social Context", "partial", 10, 15, "Only OG tags found", "Add Twitter Card tags", "medium", "P3"))
        else:
            checks.append(Check("ai_social", "social", "Social Context", "fail", 0, 15, "Missing social tags", "Add OpenGraph tags", "medium", "P3"))

        # 5. Extractability (15 pts)
        # Based on word count / text ratio (simplified)
        if word_count > 500:
            total_points += 15
            checks.append(Check("ai_extract", "extractability", "Content Extractability", "pass", 15, 15, f"Good text volume ({word_count} words)", "", "high", "P2"))
        elif word_count > 200:
            total_points += 8
            checks.append(Check("ai_extract", "extractability", "Content Extractability", "partial", 8, 15, "Low text volume", "Increase text content", "medium", "P2"))
        else:
            checks.append(Check("ai_extract", "extractability", "Content Extractability", "fail", 0, 15, "Very little text content", "Ensure content is rendered in HTML", "high", "P1"))

        return AIResult(score=total_points, checks=checks)

