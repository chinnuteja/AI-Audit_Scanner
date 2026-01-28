"""
Scoring Engine - Main orchestrator that combines all scorers.

Coordinates:
- Technical scorer
- AI scorer
- Content scorer
- Hard caps
- Confidence scoring
- Overall weighted score
"""

from dataclasses import dataclass, field
from typing import Optional

from app.services.scoring.weights import CATEGORY_WEIGHTS, SCORING_VERSION
from app.services.scoring.technical_scorer import TechnicalScorer, Check
from app.services.scoring.ai_scorer import AIScorer
from app.services.scoring.content_scorer import ContentScorer
from app.services.scoring.caps import CapsEngine
from app.services.scoring.confidence import ConfidenceScorer, ConfidenceResult
from app.logger import logger


@dataclass
class Scores:
    """All scores."""
    technical: int
    content: int
    ai: int
    overall: int


@dataclass
class AuditScores:
    """Complete audit scoring result."""
    # Scores
    scores: Scores
    
    # Confidence
    confidence: ConfidenceResult
    
    # Details
    caps_applied: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    
    # Metadata
    scoring_version: str = SCORING_VERSION


class ScoringEngine:
    """Main scoring orchestrator."""
    
    def __init__(self):
        self.technical_scorer = TechnicalScorer()
        self.ai_scorer = AIScorer()
        self.content_scorer = ContentScorer()
        self.caps_engine = CapsEngine()
        self.confidence_scorer = ConfidenceScorer()
    
    def score(
        self,
        # Page data
        status_code: Optional[int],
        redirect_count: int,
        is_https: bool,
        html: str,
        main_text: str,
        word_count: int,
        
        # Meta
        has_title: bool,
        title_length: int,
        has_meta_description: bool,
        meta_description_length: int,
        has_canonical: bool,
        canonical_matches_url: bool,
        has_noindex: bool,
        has_viewport: bool,
        h1_count: int,
        h2_count: int,
        heading_order_valid: bool,
        
        # NEW: Additional meta
        has_charset: bool,
        has_html_lang: bool,
        total_images: int,
        images_with_alt: int,
        internal_link_count: int,
        external_link_count: int,
        
        # External data
        has_sitemap: bool,
        robots_available: bool,
        ai_bots_allowed: list[str],
        ai_bots_blocked: list[str],
        llms_txt_exists: bool,
        llms_txt_quality: int,
        has_schema: bool,
        schema_types: list[str],
        has_og_tags: bool,
        has_twitter_cards: bool,
        has_faq_schema: bool,
        has_published_date: bool,
        has_trust_signals: bool,
        has_clear_purpose: bool,
        
        # Performance
        perf_available: bool,
        performance_score: Optional[int]
    ) -> AuditScores:
        """Run all scorers and combine results.
        
        Returns:
            AuditScores with all scores, checks, and metadata
        """
        logger.info("Running scoring engine...")
        
        # Run individual scorers
        technical_result = self.technical_scorer.score(
            status_code=status_code,
            redirect_count=redirect_count,
            has_canonical=has_canonical,
            canonical_matches_url=canonical_matches_url,
            has_noindex=has_noindex,
            has_sitemap=has_sitemap,
            has_robots_txt=robots_available,
            performance_score=performance_score,
            has_viewport=has_viewport,
            is_https=is_https,
            has_title=has_title,
            title_length=title_length,
            has_meta_description=has_meta_description,
            meta_description_length=meta_description_length,
            h1_count=h1_count,
            heading_order_valid=heading_order_valid,
            # NEW params
            has_charset=has_charset,
            has_html_lang=has_html_lang,
            total_images=total_images,
            images_with_alt=images_with_alt,
            internal_links=internal_link_count,
            external_links=external_link_count
        )
        
        ai_result = self.ai_scorer.score(
            ai_bots_allowed=ai_bots_allowed,
            ai_bots_blocked=ai_bots_blocked,
            llms_txt_exists=llms_txt_exists,
            llms_txt_quality=llms_txt_quality,
            has_schema=has_schema,
            schema_types=schema_types,
            has_og_tags=has_og_tags,
            has_twitter_cards=has_twitter_cards,
            has_faq_schema=has_faq_schema,
            word_count=word_count
        )
        
        content_result = self.content_scorer.score(
            word_count=word_count,
            h1_count=h1_count,
            h2_count=h2_count,
            has_clear_purpose=has_clear_purpose,
            has_trust_signals=has_trust_signals,
            internal_link_count=internal_link_count,
            external_link_count=external_link_count,
            has_published_date=has_published_date,
            main_text=main_text
        )
        
        # Calculate weighted overall
        w = CATEGORY_WEIGHTS
        overall = int(
            (ai_result.score * w.ai_seo / 100) +
            (content_result.score * w.content / 100) +
            (technical_result.score * w.technical / 100)
        )
        
        # Apply hard caps
        major_bots = {"GPTBot", "ClaudeBot", "Google-Extended"}
        # Intersection of blocked bots and major bots
        major_bots_blocked = len([b for b in ai_bots_blocked if b in major_bots])
        
        caps_result = self.caps_engine.apply(
            technical=technical_result.score,
            content=content_result.score,
            ai=ai_result.score,
            overall=overall,
            status_code=status_code,
            has_noindex=has_noindex,
            ai_bots_blocked=major_bots_blocked >= 1  # Cap if ANY major bot is blocked
        )
        
        # Recompute overall from capped subscores (pro-level consistency)
        capped_overall = int(
            (caps_result.ai * w.ai_seo / 100) +
            (caps_result.content * w.content / 100) +
            (caps_result.technical * w.technical / 100)
        )
        # Apply the cap's overall limit (if any was set by status/noindex)
        final_overall = min(capped_overall, caps_result.overall)
        
        # Calculate confidence
        confidence = self.confidence_scorer.score(
            html_available=bool(html),
            robots_available=robots_available,
            llms_txt_checked=True,  # We always attempt llms.txt fetch in audit_runner
            schema_extracted=has_schema,
            perf_available=perf_available,
            sitemap_available=has_sitemap,
            meta_extracted=has_title or has_meta_description
        )
        
        # Combine all checks
        all_checks = (
            technical_result.checks +
            ai_result.checks +
            content_result.checks
        )
        
        logger.info(
            f"Scores: tech={caps_result.technical}, ai={caps_result.ai}, "
            f"content={caps_result.content}, overall={final_overall}"
        )
        
        return AuditScores(
            scores=Scores(
                technical=caps_result.technical,
                content=caps_result.content,
                ai=caps_result.ai,
                overall=final_overall
            ),
            confidence=confidence,
            caps_applied=caps_result.caps_applied,
            labels=caps_result.labels,
            checks=all_checks
        )
