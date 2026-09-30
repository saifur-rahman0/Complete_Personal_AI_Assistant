import ipaddress
import socket
from typing import Tuple
from urllib.parse import urlparse

FORBIDDEN_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "instance-data",
}

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC1918 Private
    ipaddress.ip_network("172.16.0.0/12"),     # RFC1918 Private
    ipaddress.ip_network("192.168.0.0/16"),    # RFC1918 Private
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-Local
]


def is_safe_url(url: str) -> Tuple[bool, str]:
    """
    Validates that a URL is strictly safe for scraping.
    Blocks SSRF attempts against internal networks, loopback, cloud metadata, and invalid schemes.
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."

    try:
        parsed = urlparse(url.strip())
    except Exception as e:
        return False, f"Invalid URL structure: {e}"

    # 1. Scheme check
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported scheme '{parsed.scheme}'. Only 'http' and 'https' are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL missing valid hostname."

    hostname_lower = hostname.lower()

    # 2. Fast check against known forbidden hostnames
    if hostname_lower in FORBIDDEN_HOSTS or hostname_lower.endswith(".internal"):
        return False, f"Access to internal host '{hostname}' is blocked by SSRF policy."

    # 3. DNS resolution & IP check
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as e:
        return False, f"DNS resolution failed for '{hostname}': {e}"
    except Exception as e:
        return False, f"Could not resolve host '{hostname}': {e}"

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"Invalid IP address resolved: '{ip_str}'"

        # Check if IP falls within any blocked network
        for blocked_net in BLOCKED_IP_NETWORKS:
            if ip_obj in blocked_net:
                return False, f"Access to restricted IP '{ip_str}' ({blocked_net}) is blocked by SSRF policy."

        # Verify not loopback, private, link_local, or reserved
        if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_reserved:
            return False, f"Target IP '{ip_str}' is private/reserved and cannot be accessed."

    return True, "URL is safe"
