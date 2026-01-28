"""
PDF Generator Service - Generate premium audit reports.

Uses WeasyPrint to convert HTML/CSS templates into PDF.
"""

import os
import base64
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

from app.logger import logger
from app.services.scoring.engine import AuditScores

# Map sub-categories to main sections
CATEGORY_MAP = {
    # Technical
    "crawlability": "technical",
    "performance": "technical",
    "hygiene": "technical",
    
    # AI SEO
    "ai_access": "ai",
    "llms_txt": "ai",
    "schema": "ai",
    "social": "ai",
    "extractability": "ai",
    
    # Content
    "clarity": "content",
    "structure": "content",
    "completeness": "content",
    "freshness": "content",
    "trust_auth": "content",
    "readability": "content"
}

class PdfGenerator:
    """Generate PDF reports from audit data."""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        
    def generate(self, audit_results: AuditScores, url: str) -> bytes:
        """Generate PDF bytes from audit results.
        
        Args:
            audit_results: Complete audit scores and checks
            url: The audited URL
            
        Returns:
            bytes: PDF file content
        """
        try:
            # 1. Prepare data
            checks_by_category = {
                "technical": [],
                "content": [],
                "ai": []
            }
            
            # Sort checks into buckets
            for check in audit_results.checks:
                main_cat = CATEGORY_MAP.get(check.category)
                if main_cat:
                    checks_by_category[main_cat].append(check)
                else:
                    # Fallback for unknown categories
                    logger.warning(f"Unknown category {check.category} for check {check.id}")
                    checks_by_category["technical"].append(check)
            
            # Get logo base64
            logo_path = os.path.join(self.template_dir, "logo.txt")
            logo_b64 = ""
            if os.path.exists(logo_path):
                with open(logo_path, "r") as f:
                    logo_b64 = f.read().strip()
            
            # 2. Render HTML
            template = self.env.get_template("audit_report.html")
            html_string = template.render(
                url=url,
                date=datetime.now().strftime("%B %d, %Y"),
                scores=audit_results.scores,
                checks_by_category=checks_by_category,
                logo_base64=logo_b64,
                css_path=os.path.join(self.template_dir, "audit_report.css").replace("\\", "/")
            )
            
            # 3. Convert to PDF
            # Note: base_url is needed for resolving relative paths (though we use absolute/base64 mostly)
            params = {
                "string": html_string,
                "base_url": self.template_dir
            }
            
            pdf_bytes = HTML(**params).write_pdf()
            
            logger.info(f"Generated PDF report for {url} ({len(pdf_bytes)} bytes)")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise e
