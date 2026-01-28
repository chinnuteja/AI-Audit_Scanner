import httpx
import time
import sys

API_BASE = "http://localhost:8000/api/v1"
TARGET_URL = "https://www.svata.in/"

def run_audit():
    print(f"Starting audit for {TARGET_URL}...")
    try:
        # Start Audit
        print("Sending POST request to start audit...")
        resp = httpx.post(f"{API_BASE}/audit", json={"url": TARGET_URL, "include_perf": False}, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        job_id = data["job_id"]
        print(f"Audit started. Job ID: {job_id}")

        # Poll
        while True:
            status_resp = httpx.get(f"{API_BASE}/audit/{job_id}", timeout=10.0)
            status_resp.raise_for_status()
            job_data = status_resp.json()
            status = job_data["status"]
            print(f"Status: {status}")

            if status == "completed":
                print("Audit completed!")
                break
            elif status == "failed":
                print(f"Audit failed: {job_data.get('error')}")
                return
            
            time.sleep(2)

        # Download PDF
        print("Downloading PDF...")
        pdf_resp = httpx.get(f"{API_BASE}/audit/{job_id}/pdf", timeout=60.0)
        pdf_resp.raise_for_status()
        
        filename = "svata_in_audit_report.pdf"
        with open(filename, "wb") as f:
            f.write(pdf_resp.content)
        print(f"PDF saved to {filename}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_audit()
