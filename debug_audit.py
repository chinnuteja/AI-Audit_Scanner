
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.services.audit_runner import AuditRunner
from app.services.pdf_generator import PdfGenerator
from app.schemas.audit_result import AuditResult

async def main():
    url = "https://www.svata.in/"
    print(f"Running audit for {url}...")
    
    runner = AuditRunner()
    try:
        result = await runner.run(url, job_id="debug-job-123")
        
        print(f"Status: {result.status}")
        if result.error:
            print(f"Error: {result.error}")
        
        if result.scores:
            print("Scores present:")
            print(result.scores)
        else:
            print("Scores are None!")
            
        print(f"Checks count: {len(result.checks)}")
        if result.checks:
            print(f"First check: {result.checks[0]}")
            
        # Try generating PDF
        if result.status == "completed":
            print("Generating PDF...")
            generator = PdfGenerator()
            pdf_bytes = generator.generate(result, result.final_url)
            print(f"PDF generated: {len(pdf_bytes)} bytes")
            with open("debug_report.pdf", "wb") as f:
                f.write(pdf_bytes)
            print("Saved debug_report.pdf")
            
    except Exception as e:
        print(f"Exception during run: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
