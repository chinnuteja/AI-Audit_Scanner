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
from app.services.scoring.technical_scorer import Check
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
        has_clear_purpose: bool,  # From LLM or heuristic
        has_trust_signals: bool,  # Contact, about, testimonials
        internal_link_count: int,
        external_link_count: int,
        has_published_date: bool,
        main_text: str
    ) -> ContentScore:
        """Score content quality.
        
        Returns:
            ContentScore with total and individual checks
        """
        checks = []
        w = CONTENT_WEIGHTS
        text_lower = main_text.lower()
        
        # === CLARITY & INTENT (20 pts) ===
        
        # Detect clarity heuristically
        has_what = any(x in text_lower for x in ["we offer", "we provide", "our service", "about us", "who we are"])
        has_who = any(x in text_lower for x in ["for you", "customers", "clients", "businesses", "teams", "best for"])
        clarity_signals = sum([has_what, has_who, has_clear_purpose])
        
        if clarity_signals >= 2:
            pts = w.clarity
            status = "pass"
            evidence = "Clear purpose and audience defined"
        elif clarity_signals == 1:
            pts = w.clarity // 2
            status = "partial"
            evidence = "Partially clear purpose"
        else:
            pts = 0
            status = "fail"
            evidence = "Unclear page purpose"
        
        checks.append(Check(
            id="clarity", name="Content Clarity", category="clarity",
            points_awarded=pts, points_possible=w.clarity,
            status=status, evidence=evidence,
            how_to_fix="Clearly state what you offer in first 100 words" if pts < w.clarity else None
        ))
        
        # === STRUCTURE & READABILITY (20 pts) ===
        
        # Heading structure (10 pts)
        if h1_count == 1 and h2_count >= 2:
            pts = w.heading_structure
            status = "pass"
            evidence = f"Good structure: 1 H1, {h2_count} H2s"
        elif h1_count >= 1 and h2_count >= 1:
            pts = w.heading_structure // 2
            status = "partial"
            evidence = f"{h1_count} H1, {h2_count} H2 (could be better)"
        else:
            pts = 0
            status = "fail"
            evidence = "Poor heading structure"
        
        checks.append(Check(
            id="heading_structure", name="Heading Structure", category="structure",
            points_awarded=pts, points_possible=w.heading_structure,
            status=status, evidence=evidence,
            how_to_fix="Use one H1 and multiple H2 headings" if pts < w.heading_structure else None
        ))
        
        # Word count (5 pts)
        if word_count >= 500:
            pts = w.word_count
            status = "pass"
            evidence = f"{word_count} words (Substantial)"
        elif word_count >= 200:
            pts = int(w.word_count * 0.6)
            status = "partial"
            evidence = f"{word_count} words (Acceptable)"
        else:
            pts = 0
            status = "fail"
            evidence = f"{word_count} words (Thin content)"
        
        checks.append(Check(
            id="word_count", name="Content Length", category="structure",
            points_awarded=pts, points_possible=w.word_count,
            status=status, evidence=evidence,
            how_to_fix="Expand content to at least 500 words" if pts < w.word_count else None
        ))
        
        # Readability (5 pts)
        avg_word_length = sum(len(word) for word in main_text.split()) / max(len(main_text.split()), 1)
        if avg_word_length <= 6:
            pts = w.readability
            status = "pass"
            evidence = "Good readability"
        elif avg_word_length <= 8:
            pts = int(w.readability * 0.6)
            status = "partial"
            evidence = "Moderate readability"
        else:
            pts = 0
            status = "fail"
            evidence = "Complex language"
        
        checks.append(Check(
            id="readability", name="Readability", category="structure",
            points_awarded=pts, points_possible=w.readability,
            status=status, evidence=evidence,
            how_to_fix="Use simpler words and shorter sentences" if pts < w.readability else None
        ))
        
        # === COMPLETENESS (10 pts) ===
        
        # Internal links (10 pts)
        if internal_link_count >= 3:
            pts = w.internal_links
            status = "pass"
            evidence = f"{internal_link_count} internal links found"
        elif internal_link_count >= 1:
            pts = w.internal_links // 2
            status = "partial"
            evidence = f"{internal_link_count} internal link found"
        else:
            pts = 0
            status = "fail"
            evidence = "No internal links"
        
        checks.append(Check(
            id="internal_links", name="Internal Links", category="completeness",
            points_awarded=pts, points_possible=w.internal_links,
            status=status, evidence=evidence,
            how_to_fix="Add links to other relevant pages on your site" if pts < w.internal_links else None
        ))
        
        # === FRESHNESS (15 pts) ===
        
        # Stricter Freshness
        if has_published_date:
            pts = w.freshness
            status = "pass"
            evidence = "Published/Updated date found"
        elif word_count > 1000: # Deep content implies some freshness/evergreen value
            pts = w.freshness // 2
            status = "partial"
            evidence = "Undated but substantial content"
        else:
            pts = 0
            status = "fail"
            evidence = "No freshness signals detected"
            
        checks.append(Check(
            id="freshness", name="Content Freshness", category="freshness",
            points_awarded=pts, points_possible=w.freshness,
            status=status, evidence=evidence,
            how_to_fix="Add explicit published or updated date" if pts < w.freshness else None
        ))
        
        # === TRUST & AUTHENTICITY (35 pts) ===
        # Author(10) + Experience(15) + Evidence(10)
        
        # Sub-weights (derived dynamically to sum to w.trust_auth)
        # We target specific ratios: Author (~28%), Experience (~42%), Evidence (~28%)
        # But to be safe and clean, let's hardcode the split of the Trust bucket here 
        # OR better: add sub-weights to weights.py. 
        # For now, we will compute them as portions of w.trust_auth to respect the parent weight.
        
        w_trust = w.trust_auth
        # Split: Author=30%, Experience=40%, Evidence=30%
        pts_author_max = int(w_trust * 0.3)
        pts_exp_max = int(w_trust * 0.4)
        pts_evid_max = w_trust - pts_author_max - pts_exp_max # Remainder ensures sum matches
        
        # 1. Author & Accountability
        author_keywords = ["written by", "author:", "byline", "editorial", "reviewer"]
        found_byline = sum(1 for kw in author_keywords if kw in text_lower)
        has_social = "linkedin.com" in text_lower or "twitter.com" in text_lower
        
        if has_trust_signals or (found_byline >= 1 and has_social):
            pts = pts_author_max
            status = "pass"
            evidence = "Author / Accountability signals found"
        elif found_byline >= 1:
            pts = pts_author_max // 2
            status = "partial"
            evidence = "Author name found but no profile/trust links"
        else:
            pts = 0
            status = "fail"
            evidence = "Missing Author or Trust signals"
            
        checks.append(Check(
            id="trust_author", name="Author & Accountability", category="trust_auth",
            points_awarded=pts, points_possible=pts_author_max,
            status=status, evidence=evidence,
            how_to_fix="Add specific Author bio or link to About/Contact pages" if pts < pts_author_max else None
        ))
        
        # 2. First-Hand Experience
        pronouns_count = sum(text_lower.count(p) for p in ["i ", "we ", "my ", "our "])
        experience_verbs = ["tested", "tried", "analyzed", "reviewed", "experienced", "discovered", "learned", "built", "interviewed"]
        has_exp_verbs = any(v in text_lower for v in experience_verbs)
        has_numbers = bool(re.search(r'(\d+%|\$\d+|\d+\.\d+|years|months|hours)', text_lower))
        heading_keywords = ["result", "case study", "experiment", "benchmark", "before", "after"]
        has_exp_heading = any(k in text_lower for k in heading_keywords)
        
        strong_experience = (pronouns_count >= 2) and (has_exp_verbs or has_numbers or has_exp_heading)
        
        if strong_experience:
            pts = pts_exp_max
            status = "pass"
            evidence = "Strong experience signals (Pronouns + Data/Verbs)"
        elif pronouns_count >= 2:
            pts = pts_exp_max // 2
            status = "partial"
            evidence = "Uses personal language but lacks specific data/verbs"
        else:
            pts = 0
            status = "fail"
            evidence = "Generic / Impersonal tone"
            
        checks.append(Check(
            id="trust_experience", name="Experience Signals", category="trust_auth",
            points_awarded=pts, points_possible=pts_exp_max,
            status=status, evidence=evidence,
            how_to_fix="Demonstrate experience: 'We tested...' + numbers/results" if pts < pts_exp_max else None
        ))
        
        # 3. Evidence & Citations
        citation_keywords = ["according to", "source:", "study", "report", "cited", "reference"]
        has_citation_kw = any(kw in text_lower for kw in citation_keywords)
        
        if external_link_count >= 1 and has_citation_kw:
            pts = pts_evid_max
            status = "pass"
            evidence = f"Citations present ({external_link_count} ext links)"
        elif external_link_count >= 1:
            pts = int(pts_evid_max * 0.6)
            status = "partial" 
            evidence = f"{external_link_count} external links (add citation context)"
        elif has_citation_kw:
            pts = int(pts_evid_max * 0.3)
            status = "partial"
            evidence = "Citation terms used but no external links found"
        else:
            pts = 0
            status = "fail"
            evidence = "No evidence or external citations"
            
        checks.append(Check(
            id="trust_evidence", name="Evidence & Citations", category="trust_auth",
            points_awarded=pts, points_possible=pts_evid_max,
            status=status, evidence=evidence,
            how_to_fix="Cite authoritative sources with external links" if pts < pts_evid_max else None
        ))
        
        # Calculate Strict Total (No normalization drift)
        total = sum(c.points_awarded for c in checks)
        # max_total should be exactly 100 based on weights.py
        # Check correctness implies max_total matches sum(weights)
        
        logger.debug(f"Content score: {total}/100")
        
        return ContentScore(score=total, checks=checks)
