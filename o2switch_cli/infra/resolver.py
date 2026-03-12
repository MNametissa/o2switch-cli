from __future__ import annotations

import dns.exception
import dns.resolver

from o2switch_cli.core.models import VerificationStatus


class DNSResolver:
    def __init__(self, timeout: float = 3.0, lifetime: float = 5.0) -> None:
        self._resolver = dns.resolver.Resolver(configure=True)
        self._resolver.timeout = timeout
        self._resolver.lifetime = lifetime

    def resolve_a(self, hostname: str) -> list[str]:
        answer = self._resolver.resolve(hostname, "A")
        return sorted({record.address for record in answer})

    def verify_a(self, hostname: str, expected_ip: str | None = None) -> tuple[VerificationStatus, list[str]]:
        try:
            addresses = self.resolve_a(hostname)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            if expected_ip is None:
                return VerificationStatus.RESOLVED_MATCHES_TARGET, []
            return VerificationStatus.LOOKUP_FAILED, []
        except (dns.exception.DNSException, OSError):
            return VerificationStatus.LOOKUP_FAILED, []
        if expected_ip is None:
            return VerificationStatus.RESOLVED_MATCHES_TARGET, addresses
        if expected_ip in addresses:
            return VerificationStatus.RESOLVED_MATCHES_TARGET, addresses
        return VerificationStatus.RESOLVED_MISMATCH, addresses
