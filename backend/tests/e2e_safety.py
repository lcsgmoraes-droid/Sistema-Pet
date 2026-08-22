from urllib.parse import urlparse


PRODUCTION_DOMAINS = frozenset(
    {
        "corepet.com.br",
        "mlprohub.com.br",
    }
)


def is_production_base_url(value: str) -> bool:
    hostname = (urlparse(value).hostname or "").lower()
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in PRODUCTION_DOMAINS
    )
