from __future__ import annotations

from o2switch_cli.core.cpanel_client import CpanelClient
from o2switch_cli.core.errors import NotFoundAppError
from o2switch_cli.core.models import DomainDescriptor, DomainType
from o2switch_cli.core.validators import normalize_hostname, select_root_domain


class DomainService:
    def __init__(self, client: CpanelClient) -> None:
        self._client = client

    def list_domains(self) -> list[DomainDescriptor]:
        payload = self._client.list_domains().data or {}
        descriptors: list[DomainDescriptor] = []

        def append_many(domains: list[str], domain_type: DomainType) -> None:
            for item in domains:
                descriptors.append(
                    DomainDescriptor(
                        domain=normalize_hostname(item),
                        type=domain_type,
                        eligible_for_subdomain_creation=domain_type is not DomainType.SUBDOMAIN,
                        has_dns_zone=True,
                    )
                )

        main_domain = payload.get("main_domain")
        if isinstance(main_domain, str) and main_domain:
            descriptors.append(
                DomainDescriptor(
                    domain=normalize_hostname(main_domain),
                    type=DomainType.MAIN,
                    eligible_for_subdomain_creation=True,
                    has_dns_zone=True,
                )
            )

        append_many(payload.get("addon_domains", []) or [], DomainType.ADDON)
        append_many(payload.get("parked_domains", []) or [], DomainType.PARKED)
        append_many(payload.get("sub_domains", []) or [], DomainType.SUBDOMAIN)
        deduped = {item.domain: item for item in descriptors}
        return sorted(deduped.values(), key=lambda item: (item.type.value, item.domain))

    def root_domains(self) -> list[str]:
        return [item.domain for item in self.list_domains() if item.type is not DomainType.SUBDOMAIN]

    def search(self, term: str) -> list[DomainDescriptor]:
        needle = term.strip().lower()
        return [item for item in self.list_domains() if needle in item.domain]

    def get_domain_descriptor(self, domain: str, operation: str) -> DomainDescriptor:
        target = normalize_hostname(domain)
        for item in self.list_domains():
            if item.domain == target:
                return item
        raise NotFoundAppError(operation, "Root domain was not found on the account.", target)

    def resolve_root_domain(self, hostname: str, operation: str) -> str:
        return select_root_domain(hostname, self.root_domains(), operation)
