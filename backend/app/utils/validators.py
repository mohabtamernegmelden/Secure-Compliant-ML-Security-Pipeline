import html
import re

def sanitize_input_text(text: str) -> str:
    """
    Sanitize text inputs to prevent Cross-Site Scripting (XSS) and injection attacks.
    Escapes HTML characters and strips leading/trailing spaces.
    """
    if not isinstance(text, str):
        return text
    # Escape HTML special characters
    cleaned = html.escape(text)
    # Strip any potential carriage returns or line feeds to prevent log injection
    cleaned = re.sub(r"[\r\n]", "", cleaned)
    return cleaned.strip()

def validate_ip_format(ip: str) -> bool:
    """
    Validate that a string conforms to IPv4 or IPv6 format.
    """
    ipv4_pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}$"
    
    return bool(re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip))
