"""
Content Scorer - Evaluate content quality and completeness.

Rubric (v2.0 - World Class):
- Clarity & Intent (20 pts)
- Structure & Readability (20 pts)
- Completeness (10 pts)
- Freshness (15 pts)
- Trust & Authenticity (35 pts)
"""

from dataclasses import dataclass, field
import re

from app.services.scoring.weights import CONTENT_WEIGHTS
from app.services.scoring.models import Check
from app.logger import logger


@dataclass
class ContentScore:
    """Content scoring result."""
    score: int  # 0-100
    checks: list[Check] = field(default_factory=list)


class ContentScorer:
    """Score content quality factors."""
    
    def score(
        self,
        word_count: int,
        h1_count: int,
        h2_count: int,
        has_clear_purpose: bool,
        has_trust_signals: bool,
        internal_link_count: int,
        external_link_count: int,
        has_published_date: bool,
        main_text: str
    ) -> ContentScore:
        """Score content quality.
        Uses STRICT scoring (sum of awarded points).
        """
        checks = []
        w = CONTENT_WEIGHTS
        text_lower = main_text.lower()
        
        # Helper
        def add_check(id, cat, name, pts, max_pts, condition, evidence_pass, evidence_fail, fix="", severity="P2"):
            if condition:
                checks.append(Check(id, cat, name, "pass", pts, max_pts, evidence_pass, "", "high", severity))
            else:
                checks.append(Check(id, cat, name, "fail", 0, max_pts, evidence_fail, fix, "high", severity))

        # === CLARITY & INTENT (20 pts) ===
        
        has_what = any(x in text_lower for x in ["we offer", "we provide", "our service", "about us", "who we are"])
        has_who = any(x in text_lower for x in ["for you", "customers", "clients", "businesses", "teams", "best for"])
        clarity_signals = sum([has_what, has_who, has_clear_purpose])
        
        if clarity_signals >= 2:
            checks.append(Check("clarity", "clarity", "Content Clarity", "pass", w.clarity, w.clarity, "Clear purpose and audience", "", "high", "P1"))
        elif clarity_signals == 1:
            checks.append(Check("clarity", "clarity", "Content Clarity", "partial", w.clarity // 2, w.clarity, "Partially clear purpose", "Define audience clearly", "high", "P1"))
        else:
            checks.append(Check("clarity", "clarity", "Content Clarity", "fail", 0, w.clarity, "Unclear purpose", "State what you offer in first 100 words", "high", "P1"))
        
        # === STRUCTURE & READABILITY (20 pts) ===
        
        # Heading structure (10 pts)
        if h1_count == 1 and h2_count >= 2:
            checks.append(Check("heading_structure", "structure", "Heading Structure", "pass", w.heading_structure, w.heading_structure, f"Good structure (1 H1, {h2_count} H2s)", "", "high", "P2"))
        elif h1_count >= 1 and h2_count >= 1:
            checks.append(Check("heading_structure", "structure", "Heading Structure", "partial", w.heading_structure // 2, w.heading_structure, f"Basic structure ({h1_count} H1, {h2_count} H2)", "Use more H2 subheadings", "medium", "P2"))
        else:
            checks.append(Check("heading_structure", "structure", "Heading Structure", "fail", 0, w.heading_structure, "Poor heading structure", "Use one H1 and multiple H2s", "high", "P2"))
        
        # Word count (5 pts)
        if word_count >= 500:
            checks.append(Check("word_count", "structure", "Content Length", "pass", w.word_count, w.word_count, f"{word_count} words", "", "medium", "P2"))
        elif word_count >= 200:
             checks.append(Check("word_count", "structure", "Content Length", "partial", int(w.word_count * 0.6), w.word_count, f"{word_count} words", "Expand content", "medium", "P2"))
        else:
             checks.append(Check("word_count", "structure", "Content Length", "fail", 0, w.word_count, f"{word_count} words", "Content too thin", "high", "P2"))
        
        # Readability (5 pts)
        avg_word_length = sum(len(word) for word in main_text.split()) / max(len(main_text.split()), 1)
        if avg_word_length <= 6:
            add_check("readability", "structure", "Readability", w.readability, w.readability, True, "Good readability", "", "", "P2")
        elif avg_word_length <= 8:
            checks.append(Check("readability", "structure", "Readability", "partial", int(w.readability * 0.6), w.readability, "Moderate readability", "Use simpler words", "medium", "P2"))
        else:
            add_check("readability", "structure", "Readability", w.readability, w.readability, False, "", "Complex language", "Simplify content", "P2")

        # === COMPLETENESS (10 pts) ===
        
        # Internal links (10 pts)
        if internal_link_count >= 3:
             add_check("internal_links", "completeness", "Internal Links", w.internal_links, w.internal_links, True, f"{internal_link_count} links", "", "", "P2")
        elif internal_link_count >= 1:
             checks.append(Check("internal_links", "completeness", "Internal Links", "partial", w.internal_links // 2, w.internal_links, f"{internal_link_count} link", "Add more internal links", "medium", "P2"))
        else:
             add_check("internal_links", "completeness", "Internal Links", w.internal_links, w.internal_links, False, "", "No internal links", "Add internal links", "P2")

        # === FRESHNESS (15 pts) ===
        if has_published_date:
            add_check("freshness", "freshness", "Content Freshness", w.freshness, w.freshness, True, "Date found", "", "", "P2")
        elif word_count > 1000:
            checks.append(Check("freshness", "freshness", "Content Freshness", "partial", w.freshness // 2, w.freshness, "Undated but deep content", "Add published date", "medium", "P2"))
        else:
            add_check("freshness", "freshness", "Content Freshness", w.freshness, w.freshness, False, "", "No date detected", "Add published date", "P2")

        # === TRUST & AUTHENTICITY (35 pts: 28 Trust + 7 Humanized) ===
        
        # 1. Trust Signals (28 pts)
        # Split: Author (14) + Evidence (14)
        
        # Author & Accountability (14 pts)
        pts_author = 14
        author_keywords = ["written by", "author:", "byline", "editorial", "reviewer"]
        found_byline = sum(1 for kw in author_keywords if kw in text_lower)
        has_social = "linkedin.com" in text_lower or "twitter.com" in text_lower
        
        if has_trust_signals or (found_byline >= 1 and has_social):
             add_check("trust_author", "trust_signals", "Author & Accountability", pts_author, pts_author, True, "Author/Trust signals found", "", "", "P1")
        elif found_byline >= 1:
             checks.append(Check("trust_author", "trust_signals", "Author & Accountability", "partial", pts_author // 2, pts_author, "Author name found", "Add bio/social links", "medium", "P1"))
        else:
             add_check("trust_author", "trust_signals", "Author & Accountability", pts_author, pts_author, False, "", "Missing author info", "Add author bio", "P1")
             
        # Evidence & Citations (14 pts)
        pts_evid = 14
        citation_keywords = ["according to", "source:", "study", "report", "cited", "reference"]
        has_citation_kw = any(kw in text_lower for kw in citation_keywords)
        
        if external_link_count >= 1 and has_citation_kw:
             add_check("trust_evidence", "trust_signals", "Evidence & Citations", pts_evid, pts_evid, True, "Citations with links", "", "", "P1")
        elif external_link_count >= 1:
             checks.append(Check("trust_evidence", "trust_signals", "Evidence & Citations", "partial", int(pts_evid * 0.6), pts_evid, "Links present", "Add citation context", "medium", "P1"))
        elif has_citation_kw:
             checks.append(Check("trust_evidence", "trust_signals", "Evidence & Citations", "partial", int(pts_evid * 0.3), pts_evid, "Citation terms used", "Add external links", "medium", "P1"))
        else:
             add_check("trust_evidence", "trust_signals", "Evidence & Citations", pts_evid, pts_evid, False, "", "No citations", "Cite sources", "P1")

        # 2. Humanized Content (7 pts)
        # Replacing "Experience Signals"
        pts_human = w.humanized_content
        pronouns_count = sum(text_lower.count(p) for p in ["i ", "we ", "my ", "our "])
        experience_verbs = ["tested", "tried", "analyzed", "reviewed", "experienced", "discovered", "built", "interviewed"]
        has_exp_verbs = any(v in text_lower for v in experience_verbs)
        has_numbers = bool(re.search(r'(\d+%|\$\d+|\d+\.\d+|years|months|hours)', text_lower))
        
        # Logic: First-hand experience + Specific numbers
        is_humanized = (pronouns_count >= 1) and (has_exp_verbs or has_numbers)
        
        if is_humanized:
             add_check("humanized_content", "trust_signals", "Experience Signals", pts_human, pts_human, True, "First-hand experience detected", "", "", "P1")
        elif pronouns_count >= 1:
             checks.append(Check("humanized_content", "trust_signals", "Experience Signals", "partial", pts_human // 2, pts_human, "Personal tone used", "Add specific data/results", "medium", "P1"))
        else:
             add_check("humanized_content", "trust_signals", "Experience Signals", pts_human, pts_human, False, "", "Generic content", "Add personal experience & data", "P1")

        # Calculate Strict Total
        total = sum(c.points_awarded for c in checks)
        
        logger.debug(f"Content score: {total}/100")
        
        return ContentScore(score=int(total), checks=checks)
