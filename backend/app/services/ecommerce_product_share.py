"""HTML inicial do link compartilhado, legivel sem executar o frontend."""

import json
import os
import re
from html import escape, unescape
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit


def _http_url(value: str | None, base_url: str = "") -> str:
    raw = str(value or "").strip()
    if not raw or "\\" in raw or any(ord(char) < 32 for char in raw):
        return ""
    try:
        parsed = urlsplit(urljoin(f"{base_url}/", raw) if base_url else raw)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            return ""
        # Valida tambem portas invalidas antes de publicar a URL.
        parsed.port
        return urlunsplit(parsed._replace(fragment=""))
    except ValueError:
        return ""


def product_share_public_base_url() -> str:
    configured = (
        os.getenv("ECOMMERCE_PUBLIC_BASE_URL")
        or os.getenv("ECOMMERCE_BASE_URL")
        or os.getenv("FRONTEND_URL")
        or "https://corepet.com.br"
    )
    valid = _http_url(configured) or "https://corepet.com.br"
    parsed = urlsplit(valid)
    # As rotas publicas sao relativas a origem, nunca a um caminho de API.
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _plain_description(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]*>", " ", str(value))).split())[:200]


def render_product_share_html(tenant, product: dict, public_base_url: str) -> str:
    base_url = _http_url(public_base_url) or "https://corepet.com.br"
    parsed_base = urlsplit(base_url)
    base_url = urlunsplit((parsed_base.scheme, parsed_base.netloc, "", "", ""))
    tenant_ref = str(tenant.ecommerce_slug or tenant.id)
    product_id = int(product["id"])
    share_url = (
        f"{base_url}/api/ecommerce/compartilhar/produtos/{product_id}?"
        f"{urlencode({'tenant': tenant_ref})}"
    )
    destination = (
        f"{base_url}/ecommerce?"
        f"{urlencode({'tenant': tenant_ref, 'produto': product_id})}"
    )
    product_name = str(product.get("nome") or "Produto")
    store_name = str(tenant.name or "Loja online")
    title = f"{product_name} | {store_name}"
    description = _plain_description(
        product.get("descricao")
        or getattr(tenant, "ecommerce_descricao", None)
        or f"Confira {product_name} na {store_name}."
    )
    image_candidates = [product.get("imagem_principal")]
    for item in product.get("imagens") or []:
        image_candidates.append(item.get("url") if isinstance(item, dict) else item)
    image_candidates.append(getattr(tenant, "logo_url", None))
    image_url = next(
        (url for value in image_candidates if (url := _http_url(value, base_url))),
        "",
    )
    image_tags = ""
    image_content = ""
    if image_url:
        image_tags = (
            f'<meta property="og:image" content="{escape(image_url, quote=True)}">\n'
            f'<meta property="og:image:alt" content="{escape(product_name, quote=True)}">\n'
            f'<meta name="twitter:image" content="{escape(image_url, quote=True)}">'
        )
        image_content = (
            f'<img src="{escape(image_url, quote=True)}" '
            f'alt="{escape(product_name, quote=True)}" width="300">'
        )

    # JSON seguro dentro de script: mesmo nomes/refs malformados nao fecham a tag.
    destination_json = json.dumps(destination, ensure_ascii=True).replace(
        "<", "\\u003c"
    )
    return f"""<!doctype html>
<html lang="pt-BR" prefix="og: https://ogp.me/ns#">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description, quote=True)}">
<meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(description, quote=True)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{escape(store_name, quote=True)}">
<meta property="og:locale" content="pt_BR">
<meta property="og:url" content="{escape(share_url, quote=True)}">
<link rel="canonical" href="{escape(share_url, quote=True)}">
<meta name="twitter:card" content="{"summary_large_image" if image_url else "summary"}">
<meta name="twitter:title" content="{escape(title, quote=True)}">
<meta name="twitter:description" content="{escape(description, quote=True)}">
{image_tags}
</head>
<body>
<h1>{escape(product_name)}</h1>
{image_content}
<p>{escape(description)}</p>
<a href="{escape(destination, quote=True)}">Ver produto na {escape(store_name)}</a>
<script>window.location.replace({destination_json});</script>
</body>
</html>"""
