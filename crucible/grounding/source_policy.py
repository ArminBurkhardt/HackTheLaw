from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml


DEFAULT_POLICY_PATH = Path(__file__).with_name("allowed_sources.yaml")


@dataclass(frozen=True)
class SourcePolicy:
    allowed_domains: tuple[str, ...]

    def allows(self, url: str) -> bool:
        host = normalized_host(url)
        if not host:
            return False
        return any(host == domain or host.endswith(f".{domain}") for domain in self.allowed_domains)


def load_source_policy(path: str | None = None) -> SourcePolicy:
    policy_path = Path(path).expanduser() if path else DEFAULT_POLICY_PATH
    if not policy_path.is_absolute():
        policy_path = Path.cwd() / policy_path
    data = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    domains = data.get("allowed_domains", [])
    if not isinstance(domains, list):
        raise ValueError(f"{policy_path} must define allowed_domains as a list")
    normalized = tuple(sorted({normalize_domain(str(domain)) for domain in domains if str(domain).strip()}))
    if not normalized:
        raise ValueError(f"{policy_path} must allow at least one domain")
    return SourcePolicy(allowed_domains=normalized)


def normalized_host(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return normalize_domain(parsed.hostname or "")


def normalize_domain(domain: str) -> str:
    cleaned = domain.strip().lower().rstrip(".")
    return cleaned[4:] if cleaned.startswith("www.") else cleaned
