"""
Server-Side Request Forgery (SSRF) Protection Filter
====================================================
Prevents the autonomous coding agent and browser subagent from calling:
  - localhost / 127.0.0.1 / 0.0.0.0
  - Private IPv4 & IPv6 subnets (RFC 1918 & RFC 4193)
  - Cloud metadata services (169.254.169.254)
  - Unix domain sockets
"""

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "169.254.169.254",
    "instance-data",
}


class SSRFProtectionError(ValueError):
    """Raised when an outbound URL violates SSRF safety boundaries."""


class SSRFFilter:
    """Validates URLs and destinations before network calls."""

    @staticmethod
    def validate_url(url: str, allow_local_dev: bool = False) -> str:
        """
        Parses URL, resolves DNS, and validates against private/metadata IPs.
        Raises SSRFProtectionError on violation.
        """
        if not url:
            raise SSRFProtectionError("URL cannot be empty")

        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            raise SSRFProtectionError(f"Unsupported URL scheme: {parsed.scheme}")

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise SSRFProtectionError("URL missing hostname")

        if not allow_local_dev and hostname in BLOCKED_HOSTNAMES:
            raise SSRFProtectionError(f"Access to blocked internal host '{hostname}' is denied by SSRF policy.")

        try:
            # Resolve DNS to check real IP address
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)

                # Check if loopback, private, or link-local
                if not allow_local_dev and (
                    ip_obj.is_loopback
                    or ip_obj.is_private
                    or ip_obj.is_link_local
                    or ip_obj.is_reserved
                ):
                    raise SSRFProtectionError(
                        f"SSRF violation: Host '{hostname}' resolves to restricted internal IP {ip_str}"
                    )
        except socket.gaierror as e:
            raise SSRFProtectionError(f"DNS resolution failure for host '{hostname}': {e}") from e

        return url

    @classmethod
    def is_safe_url(cls, url: str) -> bool:
        """Helper returning True if URL passes SSRF validation, False otherwise."""
        try:
            cls.validate_url(url)
            return True
        except Exception:
            return False


ssrf_filter = SSRFFilter()
