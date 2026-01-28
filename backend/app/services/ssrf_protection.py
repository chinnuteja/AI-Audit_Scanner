"""
SSRF Protection - Validate URLs to prevent server-side request forgery.
"""
import ipaddress
import socket
from urllib.parse import urlparse

from app.logger import logger


class SSRFProtection:
    """Validates URLs to prevent SSRF attacks."""
    
    # Private/internal IP ranges to block
    BLOCKED_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("0.0.0.0/8"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
    ]
    
    # Blocked hostnames
    BLOCKED_HOSTS = {
        "localhost",
        "metadata.google.internal",
        "169.254.169.254",  # AWS/GCP metadata
    }
    
    @classmethod
    def validate_url(cls, url: str) -> tuple[bool, str]:
        """
        Validate URL for SSRF vulnerabilities.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return False, f"Invalid scheme: {parsed.scheme}"
            
            # Check for empty host
            if not parsed.netloc:
                return False, "Empty hostname"
            
            hostname = parsed.hostname
            if not hostname:
                return False, "Could not parse hostname"
            
            # Check blocked hostnames
            if hostname.lower() in cls.BLOCKED_HOSTS:
                return False, f"Blocked hostname: {hostname}"
            
            # Resolve hostname to IP
            try:
                ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(ip_str)
                
                # Check against blocked ranges
                for blocked_range in cls.BLOCKED_RANGES:
                    if ip in blocked_range:
                        return False, f"IP {ip_str} is in blocked range {blocked_range}"
                        
            except socket.gaierror:
                # DNS resolution failed - allow the request to proceed
                # The actual HTTP request will fail if the host doesn't exist
                logger.warning(f"DNS resolution failed for {hostname}")
            
            return True, ""
            
        except Exception as e:
            logger.error(f"SSRF validation error: {e}")
            return False, str(e)
