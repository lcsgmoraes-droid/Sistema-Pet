import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
import requests


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ENV", "test")

pytestmark = pytest.mark.e2e_long


@dataclass(frozen=True)
class E2EConfig:
    base_url: str
    user_email: str
    user_password: str
    tenant_id: str
    blocked_path: str
    timeout_seconds: float
    prefix: str


class E2EApi:
    def __init__(self, config: E2EConfig):
        self.config = config
        self.session = requests.Session()
        self.token = ""

    def _url(self, path: str) -> str:
        return f"{self.config.base_url}{path if path.startswith('/') else '/' + path}"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": f"{self.config.prefix}-{uuid4().hex[:8]}",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.config.timeout_seconds)
        headers = self._headers()
        headers.update(kwargs.pop("headers", {}) or {})
        return self.session.request(method, self._url(path), headers=headers, **kwargs)

    def expect(
        self,
        method: str,
        path: str,
        expected_status: set[int],
        step: str,
        **kwargs: Any,
    ) -> requests.Response:
        response = self.request(method, path, **kwargs)
        assert response.status_code in expected_status, (
            f"{step} failed: expected {sorted(expected_status)}, "
            f"got {response.status_code}: {response.text[:800]}"
        )
        return response


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


@pytest.fixture(scope="module")
def e2e_config() -> E2EConfig:
    required = [
        "E2E_BASE_URL",
        "E2E_USER_EMAIL",
        "E2E_USER_PASSWORD",
        "E2E_TENANT_ID",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        pytest.skip("Plano Basico E2E skipped; missing env vars: " + ", ".join(missing))

    base_url = os.environ["E2E_BASE_URL"].rstrip("/")
    if "mlprohub.com.br" in base_url and not _env_bool("E2E_ALLOW_PRODUCTION"):
        pytest.skip(
            "Plano Basico E2E skipped; set E2E_ALLOW_PRODUCTION=true for production"
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return E2EConfig(
        base_url=base_url,
        user_email=os.environ["E2E_USER_EMAIL"].strip().lower(),
        user_password=os.environ["E2E_USER_PASSWORD"],
        tenant_id=os.environ["E2E_TENANT_ID"].strip(),
        blocked_path=os.getenv("E2E_BLOCKED_PATH") or "/banho-tosa/configuracao",
        timeout_seconds=float(os.getenv("E2E_TIMEOUT_SECONDS") or "20"),
        prefix=f"E2E-PB-{stamp}",
    )


@pytest.fixture(scope="module")
def api(e2e_config: E2EConfig) -> E2EApi:
    client = E2EApi(e2e_config)

    login = client.expect(
        "POST",
        "/auth/login-multitenant",
        {200},
        "auth.login",
        json={
            "email": e2e_config.user_email,
            "password": e2e_config.user_password,
        },
    ).json()
    client.token = login["access_token"]

    selected = client.expect(
        "POST",
        "/auth/select-tenant",
        {200},
        "auth.select_tenant",
        json={"tenant_id": e2e_config.tenant_id},
    ).json()
    client.token = selected["access_token"]

    return client


def _ensure_caixa_aberto(api: E2EApi) -> None:
    status_response = api.request("GET", "/caixas/aberto")
    if status_response.status_code == 200:
        status_payload = status_response.json()
        if status_payload and status_payload.get("status") == "aberto":
            return

    api.expect(
        "POST",
        "/caixas/abrir",
        {200, 201},
        "caixa.abrir",
        json={
            "valor_abertura": 100.0,
            "observacoes_abertura": f"{api.config.prefix} caixa E2E",
        },
    )


def _create_cliente(api: E2EApi) -> int:
    suffix = api.config.prefix[-10:]
    response = api.expect(
        "POST",
        "/clientes/",
        {200, 201},
        "clientes.create",
        json={
            "tipo_cadastro": "cliente",
            "tipo_pessoa": "PF",
            "nome": f"{api.config.prefix} Cliente",
            "telefone": f"119{suffix[-8:]}",
            "email": f"{api.config.prefix.lower()}@mlprohub.test",
            "observacoes": api.config.prefix,
        },
    )
    return int(response.json()["id"])


def _create_produto(api: E2EApi) -> tuple[int, float]:
    response = api.expect(
        "POST",
        "/produtos/",
        {200, 201},
        "produtos.create",
        json={
            "codigo": f"{api.config.prefix}-SKU",
            "nome": f"{api.config.prefix} Produto",
            "unidade": "UN",
            "preco_custo": 6.0,
            "preco_venda": 10.0,
            "estoque_minimo": 0,
            "tipo_produto": "SIMPLES",
            "anunciar_ecommerce": False,
            "anunciar_app": False,
        },
    )
    produto = response.json()
    produto_id = int(produto["id"])

    api.expect(
        "POST",
        f"/produtos/{produto_id}/entrada",
        {200, 201},
        "produtos.entrada",
        json={
            "nome_lote": f"{api.config.prefix}-LOTE",
            "quantidade": 5,
            "preco_custo": 6.0,
            "observacoes": api.config.prefix,
        },
    )

    reloaded = api.expect(
        "GET",
        f"/produtos/{produto_id}",
        {200},
        "produtos.get_after_entrada",
    ).json()
    estoque = float(reloaded.get("estoque_atual") or 0)
    assert estoque >= 5, f"produtos.entrada failed: estoque_atual={estoque}"
    return produto_id, estoque


def test_plano_basico_minimo_jornada(api: E2EApi):
    me = api.expect("GET", "/auth/me-multitenant", {200}, "auth.me").json()
    assert str(me["tenant"]["id"]) == api.config.tenant_id

    blocked = api.request("GET", api.config.blocked_path)
    assert blocked.status_code == 403, (
        f"module barrier failed for {api.config.blocked_path}: "
        f"expected 403, got {blocked.status_code}: {blocked.text[:800]}"
    )

    _ensure_caixa_aberto(api)
    cliente_id = _create_cliente(api)
    produto_id, estoque_inicial = _create_produto(api)

    venda = api.expect(
        "POST",
        "/vendas",
        {200, 201},
        "vendas.create",
        json={
            "cliente_id": cliente_id,
            "itens": [
                {
                    "tipo": "produto",
                    "produto_id": produto_id,
                    "quantidade": 1,
                    "preco_unitario": 10.0,
                    "subtotal": 10.0,
                }
            ],
            "desconto_valor": 0,
            "desconto_percentual": 0,
            "observacoes": api.config.prefix,
            "tem_entrega": False,
        },
    ).json()
    venda_id = int(venda["id"])

    finalizada = api.expect(
        "POST",
        f"/vendas/{venda_id}/finalizar",
        {200},
        "vendas.finalizar",
        json={
            "pagamentos": [
                {
                    "forma_pagamento": "pix",
                    "valor": 10.0,
                    "numero_parcelas": 1,
                }
            ]
        },
    ).json()

    venda_payload = finalizada.get("venda", finalizada)
    assert venda_payload.get("status") in {"finalizada", "concluida", "fechada"}

    produto_final = api.expect(
        "GET",
        f"/produtos/{produto_id}",
        {200},
        "produtos.get_after_venda",
    ).json()
    estoque_final = float(produto_final.get("estoque_atual") or 0)
    assert estoque_final <= estoque_inicial - 1, (
        f"estoque not decremented: inicial={estoque_inicial}, final={estoque_final}"
    )
